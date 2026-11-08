// Qamyal для macOS: запись экрана (ScreenCaptureKit + аппаратный H.264) и красная рамка по краю экрана.
// Запуск: QamyalScreen [--fps 15] [--height 1080] [--quality 27] <файл.mov>   (файл — последним, как у ffmpeg)
// Говорит с Python тем же языком, что ffmpeg в Windows (app/screen.py):
//   • в stdout — строки «out_time_us=<микросекунды с первого кадра>»: по первой Python узнаёт время первого кадра;
//   • «q» в stdin или конец stdin (программа закрылась или упала) — дописать файл и выйти.
// Файл пишется блоками по 2 с (fragmented mov): если помощник упадёт, записанное до этого сохранится.
// Рамка — окно поверх всех, щелчки проходят насквозь; в запись не попадает (исключено из фильтра захвата).
// Разрешение «Запись экрана» спрашивает macOS (Системные настройки → Конфиденциальность → Запись экрана → Qamyal).
import AppKit
import AVFoundation
import CoreMedia
import ScreenCaptureKit

setvbuf(stdout, nil, _IOLBF, 0)

func fail(_ text: String, _ code: Int32 = 2) -> Never {
    FileHandle.standardError.write((text + "\n").data(using: .utf8)!)
    exit(code)
}

// ---------- аргументы ----------
var args = Array(CommandLine.arguments.dropFirst())
guard let outPath = args.last, !outPath.hasPrefix("--"), args.count % 2 == 1 else {
    fail("использование: QamyalScreen [--fps N] [--height H] [--quality Q] [--no-frame 1] <файл.mov>")
}
func opt(_ name: String, _ def: Int) -> Int {
    if let i = args.firstIndex(of: name), i + 1 < args.count, let v = Int(args[i + 1]) { return v }
    return def
}
let fps = max(1, opt("--fps", 15))
let maxHeight = opt("--height", 1080)          // 0 — как у экрана
let quality = opt("--quality", 27)             // как crf у ffmpeg: меньше — лучше
let outURL = URL(fileURLWithPath: outPath)

final class Capture: NSObject, SCStreamOutput, SCStreamDelegate {
    let q = DispatchQueue(label: "qamyal.screen")
    var stream: SCStream?
    var writer: AVAssetWriter?
    var input: AVAssetWriterInput?
    var t0 = CMTime.invalid
    var lastPTS = CMTime.invalid
    var last: CMSampleBuffer?                  // последний кадр: на неподвижном экране повторяем его сами
    var lastPrint = 0.0
    var timer: DispatchSourceTimer?
    var finishing = false
    var frameWindow: NSWindow?

    // ---------- рамка ----------
    func showFrame(on screen: NSScreen) {
        let w = NSWindow(contentRect: screen.frame, styleMask: .borderless, backing: .buffered, defer: false)
        w.isOpaque = false
        w.backgroundColor = .clear
        w.ignoresMouseEvents = true
        w.hasShadow = false
        w.level = .screenSaver
        w.collectionBehavior = [.canJoinAllSpaces, .stationary, .ignoresCycle, .fullScreenAuxiliary]
        w.sharingType = .none
        let v = NSView(frame: NSRect(origin: .zero, size: screen.frame.size))
        v.wantsLayer = true
        v.layer?.borderWidth = 4
        v.layer?.borderColor = NSColor(calibratedRed: 0.90, green: 0.28, blue: 0.30, alpha: 1).cgColor
        w.contentView = v
        w.orderFrontRegardless()
        frameWindow = w
    }

    // ---------- запуск ----------
    func start() async {
        let content: SCShareableContent
        do {
            content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        } catch {
            fail("нет разрешения на запись экрана: Системные настройки → Конфиденциальность и безопасность → Запись экрана → включите Qamyal и перезапустите его")
        }
        let mainID = CGMainDisplayID()
        guard let display = content.displays.first(where: { $0.displayID == mainID }) ?? content.displays.first else {
            fail("не найден экран")
        }
        let screen = NSScreen.screens.first {
            ($0.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value == display.displayID
        } ?? NSScreen.main
        let scale = screen?.backingScaleFactor ?? 2
        var w = Int(Double(display.width) * scale), h = Int(Double(display.height) * scale)
        if maxHeight > 0 && h > maxHeight {
            w = Int(Double(w) * Double(maxHeight) / Double(h))
            h = maxHeight
        }
        w -= w % 2
        h -= h % 2
        // своё окно-рамку исключаем из захвата
        let mine = content.windows.filter { $0.windowID == CGWindowID(frameWindow?.windowNumber ?? -1) }
        let filter = SCContentFilter(display: display, excludingWindows: mine)
        let cfg = SCStreamConfiguration()
        cfg.width = w
        cfg.height = h
        cfg.minimumFrameInterval = CMTime(value: 1, timescale: CMTimeScale(fps))
        cfg.pixelFormat = kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange
        cfg.showsCursor = true
        cfg.queueDepth = 6

        do {
            let wr = try AVAssetWriter(outputURL: outURL, fileType: .mov)
            wr.movieFragmentInterval = CMTime(value: 2, timescale: 1)
            // битрейт по «качеству» как у crf: 27 → ~0,12 бита на пиксель в секунду при 15 к/с
            let bpp = 0.12 * pow(2.0, Double(27 - quality) / 6.0)
            let bitrate = max(500_000, Int(Double(w * h) * bpp * Double(min(fps, 15))))
            let inp = AVAssetWriterInput(mediaType: .video, outputSettings: [
                AVVideoCodecKey: AVVideoCodecType.h264,
                AVVideoWidthKey: w,
                AVVideoHeightKey: h,
                AVVideoCompressionPropertiesKey: [
                    AVVideoAverageBitRateKey: bitrate,
                    AVVideoMaxKeyFrameIntervalKey: fps * 2,
                    AVVideoMaxKeyFrameIntervalDurationKey: 2,
                    AVVideoAllowFrameReorderingKey: false,
                    AVVideoExpectedSourceFrameRateKey: fps,
                ],
            ])
            inp.expectsMediaDataInRealTime = true
            guard wr.canAdd(inp) else { fail("кодер не принял настройки") }
            wr.add(inp)
            writer = wr
            input = inp
            let s = SCStream(filter: filter, configuration: cfg, delegate: self)
            try s.addStreamOutput(self, type: .screen, sampleHandlerQueue: q)
            try await s.startCapture()
            stream = s
        } catch {
            fail("экран не записывается: \(error.localizedDescription)")
        }
        // на неподвижном экране macOS новых кадров не присылает — повторяем последний, чтобы видео шло ровно
        let t = DispatchSource.makeTimerSource(queue: q)
        t.schedule(deadline: .now() + .milliseconds(500), repeating: .milliseconds(1000 / fps))
        t.setEventHandler { [weak self] in self?.repeatLast() }
        t.resume()
        timer = t
    }

    func now() -> CMTime { CMClockGetTime(CMClockGetHostTimeClock()) }

    func append(_ sb: CMSampleBuffer, at pts: CMTime) {
        guard let wr = writer, let inp = input, !finishing else { return }
        if t0 == .invalid {
            guard wr.startWriting() else { fail("файл не создаётся: \(wr.error?.localizedDescription ?? "")", 3) }
            wr.startSession(atSourceTime: pts)
            t0 = pts
        }
        if lastPTS != .invalid && pts <= lastPTS { return }
        var timing = CMSampleTimingInfo(duration: .invalid, presentationTimeStamp: pts, decodeTimeStamp: .invalid)
        var copy: CMSampleBuffer?
        CMSampleBufferCreateCopyWithNewTiming(allocator: nil, sampleBuffer: sb, sampleTimingEntryCount: 1,
                                              sampleTimingArray: &timing, sampleBufferOut: &copy)
        guard let c = copy, inp.isReadyForMoreMediaData, inp.append(c) else { return }
        lastPTS = pts
        let sec = CMTimeGetSeconds(CMTimeSubtract(pts, t0))
        let wall = Date().timeIntervalSince1970
        if wall - lastPrint >= 0.5 || lastPrint == 0 {
            print("out_time_us=\(max(1, Int64(sec * 1_000_000)))")
            lastPrint = wall
        }
    }

    func repeatLast() {
        guard let sb = last, lastPTS != .invalid else { return }
        let n = now()
        if CMTimeGetSeconds(CMTimeSubtract(n, lastPTS)) >= 1.5 / Double(fps) { append(sb, at: n) }
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer sb: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, sb.isValid,
              let att = CMSampleBufferGetSampleAttachmentsArray(sb, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]],
              let raw = att.first?[.status] as? Int, SCFrameStatus(rawValue: raw) == .complete,
              CMSampleBufferGetImageBuffer(sb) != nil else { return }
        last = sb
        append(sb, at: CMSampleBufferGetPresentationTimeStamp(sb))
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        FileHandle.standardError.write("захват остановился: \(error.localizedDescription)\n".data(using: .utf8)!)
        finish(code: 3)
    }

    // ---------- конец ----------
    func finish(code: Int32 = 0) {
        q.async { [self] in
            if finishing { return }
            finishing = true
            timer?.cancel()
            let s = stream
            Task {
                try? await s?.stopCapture()
                q.async { [self] in
                    guard let wr = writer, t0 != .invalid else {
                        try? FileManager.default.removeItem(at: outURL)     // кадров не было — пустой файл не нужен
                        exit(code)
                    }
                    input?.markAsFinished()
                    wr.endSession(atSourceTime: now())
                    wr.finishWriting { exit(code) }
                }
            }
        }
    }
}

let cap = Capture()
let app = NSApplication.shared
app.setActivationPolicy(.accessory)            // без значка в Dock

// «q» или конец stdin — заканчиваем
Thread.detachNewThread {
    while true {
        let d = FileHandle.standardInput.availableData
        if d.isEmpty || d.contains(UInt8(ascii: "q")) { cap.finish(); break }
    }
}
signal(SIGTERM, SIG_IGN)
let term = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
term.setEventHandler { cap.finish() }
term.resume()

DispatchQueue.main.async {
    let mainID = CGMainDisplayID()
    let screen = NSScreen.screens.first {
        ($0.deviceDescription[NSDeviceDescriptionKey("NSScreenNumber")] as? NSNumber)?.uint32Value == mainID
    } ?? NSScreen.main
    if let s = screen, !CommandLine.arguments.contains("--no-frame") { cap.showFrame(on: s) }
    Task { await cap.start() }
}
app.run()
