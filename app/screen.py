"""Запись экрана во время диктофона. Картинку пишет ffmpeg кусками (после паузы — новый кусок), звук пишет Qamyal.
У каждого куска известно время первого кадра по часам, у звука — якоря «секунда записи ↔ время на часах».
После «Стоп» обработчик (worker) склеивает куски и звук в видео.mp4."""
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf

from sysdeps import (HIDDEN, find_program, hide_screen_frame, kill_with_parent, screen_encoders, screen_helper,
                     screen_inputs, show_screen_frame)

# высота кадра (0 — как у экрана), кадров в секунду, качество сжатия (меньше — лучше и тяжелее)
QUALITY = {"low": (720, 5, 30), "normal": (1080, 15, 27), "high": (0, 30, 23)}
VIDEO = "видео.mp4"
META = "экран.json"
_works = {}                # какой способ съёмки и кодер сработали — проверяем один раз за запуск программы


def ffmpeg() -> str:
    exe = find_program("ffmpeg")
    if not exe:
        raise RuntimeError("не найден ffmpeg")
    return exe


def _variants(quality: str, monitor: int) -> list:
    h, fps, q = QUALITY.get(quality, QUALITY["normal"])
    helper = screen_helper(h, fps, q)
    if helper:                       # macOS: свой помощник, пробовать нечего
        return [helper]
    scale = f"scale=-2:'min({h},ih)'," if h else ""
    out = []
    for inp, pre in screen_inputs(fps, monitor):
        for enc, pix in screen_encoders(q, fps):
            vf = ",".join(x for x in (pre, scale.rstrip(","), f"format={pix}") if x)
            out.append(inp + ["-vf", vf] + enc)
    return out


def _probe(args: list) -> bool:
    """Пробная съёмка: работают ли этот способ и кодер на этом компьютере. Не работают — ffmpeg сразу
    выходит с ошибкой. На неподвижном экране кадры могут не идти, поэтому живой через 4 с ffmpeg — тоже «работает»."""
    try:
        p = subprocess.Popen([ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", *args,
                              "-frames:v", "3", "-f", "null", "-"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **HIDDEN)
    except OSError:
        return False
    try:
        return p.wait(timeout=4) == 0
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait()
        return True


def _is_helper(args: list) -> bool:
    """Команда — свой помощник (macOS), а не аргументы для ffmpeg."""
    return bool(args) and not args[0].startswith("-")


def pick(quality: str, monitor: int) -> list:
    """Рабочий способ съёмки запоминаем; неудачу — нет (экран мог быть заблокирован, позже получится)."""
    key = (quality, monitor)
    if key not in _works:
        vs = _variants(quality, monitor)
        found = vs[0] if vs and _is_helper(vs[0]) else next((a for a in vs if _probe(a)), None)
        if not found:
            raise RuntimeError("не удалось начать съёмку экрана")
        _works[key] = found
    return _works[key]


class ScreenRecorder:
    """Пишет экран в rec-….screen-N.mkv рядом со звуком; список кусков — в rec-….screen.json."""

    def __init__(self, base: Path, quality: str, monitor: int):
        self.base, self.quality, self.monitor = base, quality, monitor
        self.args = None                 # способ съёмки выбираем при первом удачном старте
        self.segments = []
        self.proc = None
        self.error = ""
        self.closed = False              # «Стоп»: больше кусков не начинаем (сторож мог не успеть узнать)
        self.enabled = True              # экран можно выключить и снова включить посреди записи
        self.frame = None                # красная рамка: видна, пока экран действительно пишется
        self.starting = False            # кусок запускается — сторож не должен считать его упавшим
        self.lock = threading.Lock()

    @property
    def meta_path(self) -> Path:
        return self.base.with_suffix(".screen.json")

    def _save(self):
        """Атомарно: файл не бывает записан наполовину. Временный — с точкой в начале, чтобы leftovers() его не взял."""
        tmp = self.meta_path.with_name("." + self.meta_path.name + ".tmp")
        tmp.write_text(json.dumps({"quality": self.quality, "segments": self.segments},
                                  ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.meta_path)

    def start(self, settle: float = 3.0) -> None:
        """Новый кусок. Ждём первый кадр не дольше settle секунд: Desktop Duplication отдаёт его только когда
        на экране что-то изменилось, и на неподвижном слайде он может прийти позже — живой ffmpeg без кадра
        тоже считаем рабочим, время первого кадра запишется, когда кадр придёт. Звук это не задерживает:
        звук и картинка сводятся по часам."""
        with self.lock:
            if self.proc or self.closed or not self.enabled:
                return
            self.starting = True
            try:
                self._start(settle)
            finally:
                self.starting = False

    def _start(self, settle: float) -> None:
        self.args = self.args or pick(self.quality, self.monitor)
        a = self.args
        helper = _is_helper(a)
        f = self.base.with_name(f"{self.base.stem}.screen-{len(self.segments) + 1}.{'mov' if helper else 'mkv'}")
        log = self.base.with_suffix(".screen.log")
        # каждый кадр сразу на диск, блоки — по 2 с: если ffmpeg (помощник) упадёт, потеряется не больше 2 с
        cmd = [*a, str(f)] if helper else [ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *a,
                                           "-flush_packets", "1", "-cluster_time_limit", "2000",
                                           "-progress", "pipe:1", "-stats_period", "0.1", str(f)]
        with open(log, "ab") as err:          # ошибки — в файл: труба за час записи могла бы переполниться
            p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, **HIDDEN)
        kill_with_parent(p)          # Qamyal упала — ffmpeg не должен писать экран дальше
        first = threading.Event()
        seg = {"file": f.name, "v0": None}

        def watch():                 # время первого кадра по часам: сейчас минус сколько уже записано
            for line in p.stdout:
                if seg["v0"] is None and line.startswith(b"out_time_us="):
                    try:
                        us = int(line.split(b"=")[1])
                    except ValueError:
                        continue
                    if us > 0:
                        seg["v0"] = round(time.time() - us / 1e6, 3)
                        first.set()
                        with self.lock:      # stop() тоже пишет файл — не одновременно
                            if seg in self.segments:
                                self._save()

        threading.Thread(target=watch, daemon=True).start()
        first.wait(settle)
        if p.poll() is not None:     # ffmpeg не смог начать (экран заблокирован, нет доступа к видеокарте)
            self._kill(p)
            err = log.read_text("utf-8", "replace").strip()
            f.unlink(missing_ok=True)
            raise RuntimeError("экран не записывается" + (f": {err.splitlines()[-1]}" if err else ""))
        self.proc = p
        self.segments.append(seg)
        self._save()
        self.frame = self.frame or show_screen_frame(self.monitor)

    def alive(self) -> bool:
        return self.starting or (self.proc is not None and self.proc.poll() is None)

    def stop(self, final: bool = False) -> None:
        """Закрыть кусок: «q» — ffmpeg дописывает файл как положено. final — запись закончена совсем."""
        with self.lock:
            self.closed = self.closed or final
            p, self.proc = self.proc, None
            hide_screen_frame(self.frame)
            self.frame = None
            if p:
                self._kill(p)
                if self.segments:
                    self.segments[-1]["v1"] = round(time.time(), 3)
                    self._save()

    @staticmethod
    def _kill(p):
        try:
            p.stdin.write(b"q")
            p.stdin.flush()
            p.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            p.kill()
            p.wait()

    def files(self) -> list:
        return [self.meta_path] + [self.base.with_name(s["file"]) for s in self.segments]


def leftovers(audio: Path) -> list:
    """Файлы экрана, которые лежат рядом с записью звука rec-….flac."""
    return sorted(audio.parent.glob(audio.stem + ".screen*"))


def attach(audio: Path, job: Path) -> bool:
    """Переносит куски экрана в черновики задания: черновики\\экран\\."""
    files = leftovers(audio)
    if not any(f.suffix == ".json" for f in files):
        for f in files:
            f.unlink(missing_ok=True)
        return False
    d = job / "черновики" / "экран"
    d.mkdir(parents=True, exist_ok=True)
    for f in files:
        if f.suffix == ".log":
            f.unlink(missing_ok=True)
            continue
        if f.suffix != ".json" and ".screen-" not in f.name:      # чужой файл — не трогаем
            continue
        name = META if f.suffix == ".json" else f.name.split(".screen-")[1]     # «1.mkv»
        shutil.move(str(f), str(d / name))
    meta = json.loads((d / META).read_text(encoding="utf-8"))
    for s in meta["segments"]:
        s["file"] = s["file"].split(".screen-")[1]
    (d / META).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return True


def ffprobe() -> str:
    return find_program("ffprobe") or str(Path(ffmpeg()).with_name(Path(ffmpeg()).name.replace("ffmpeg", "ffprobe")))


def duration(path: Path) -> float:
    """Длина видео, с. У куска, который ffmpeg не успел закрыть (упал), длины в заголовке нет — тогда по последнему кадру."""
    probe = ffprobe()
    r = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, **HIDDEN)
    try:
        return float(r.stdout.strip())
    except ValueError:
        pass
    r = subprocess.run([probe, "-v", "error", "-select_streams", "v", "-show_entries", "packet=pts_time,duration_time",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, **HIDDEN)
    best = 0.0
    for line in r.stdout.split():
        try:
            pts, dur = (float(x or 0) for x in (line.split(",") + ["0"])[:2])
        except ValueError:
            continue
        best = max(best, pts + dur)
    return best


def timeline(segments: list, anchors: list, total: float) -> list:
    """Куски, где звук ложится на видео: [секунда записи с, по, секунда видео]. Совпадение ищем по часам:
    у звука — якоря после старта и каждой паузы, у картинки — время первого кадра каждого куска."""
    pieces = []
    for k, (r, w) in enumerate(anchors):
        end = anchors[k + 1][0] if k + 1 < len(anchors) else total
        pieces.append((r, end, w))                       # звук [r, end) записан с часов w
    out, pos = [], 0.0
    for s in segments:
        v0, dur = s["v0"], s["dur"]
        for r, end, w in pieces:
            a = max(w, v0)                               # пересечение по часам
            b = min(w + (end - r), v0 + dur)
            if b - a > 0.05:
                out.append([round(r + a - w, 3), round(r + b - w, 3), round(pos + a - v0, 3)])
        pos += dur
    return out


def mux(job: Path, wav: Path, anchors: list, progress=lambda p: None) -> list:
    """Склеивает куски экрана и звук в видео.mp4. Возвращает карту «время записи → время видео»."""
    d = job / "черновики" / "экран"
    meta = json.loads((d / META).read_text(encoding="utf-8"))
    segs = [s for s in meta["segments"] if s.get("v0") and (d / s["file"]).exists()]
    for s in segs:
        s["dur"] = duration(d / s["file"])
    segs = [s for s in segs if s["dur"] > 0.2]
    if not segs:
        return []
    audio, sr = sf.read(str(wav), dtype="int16")          # int16: три часа — 350 МБ, а не 1,4 ГБ
    if audio.ndim > 1:
        audio = audio.mean(axis=1).astype(np.int16)
    tl = timeline(segs, anchors, len(audio) / sr)
    track = np.zeros(int(sum(s["dur"] for s in segs) * sr) + 1, dtype=np.int16)
    for r0, r1, v in tl:
        a = audio[int(r0 * sr):int(r1 * sr)]
        i = int(v * sr)
        a = a[:max(0, len(track) - i)]
        track[i:i + len(a)] = a
    progress(30)
    tmp_wav, lst = d / "звук.wav", d / "куски.txt"
    sf.write(str(tmp_wav), track, sr, subtype="PCM_16")
    lst.write_text("".join(f"file '{s['file']}'\n" for s in segs), encoding="utf-8")
    out = job / VIDEO
    subprocess.run([ffmpeg(), "-nostdin", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-i", str(tmp_wav), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "64k",
                    "-movflags", "+faststart", "-shortest", str(out)],
                   check=True, capture_output=True, **HIDDEN)
    progress(90)
    shutil.rmtree(d, ignore_errors=True)        # видео собрано — куски больше не нужны
    return tl


# ---------- кадры: что было на экране, когда менялась картинка ----------

FRAMES = "кадры"
MAX_FRAMES = 300


def to_record(x: float, vmap: list) -> float:
    """Секунда видео → секунда записи (обратная карта mux)."""
    for r0, r1, v in vmap:
        if x < v + r1 - r0:
            return r0 + max(0.0, x - v)
    return vmap[-1][1] if vmap else x


def keyframes(job: Path, vmap: list, progress=lambda p: None) -> list:
    """Кадры, где сменился экран (новый слайд, другое окно): [{"t": секунда записи, "file": "кадры/….jpg"}].
    Смотрим только опорные кадры видео (раз в 2 с) — это быстро. Кадр берём, когда картинка заметно
    отличается от последнего сохранённого и уже не меняется (анимация перехода закончилась).
    Всё через ffmpeg/ffprobe — без PyAV и Pillow (на Mac их может не быть)."""
    video = job / VIDEO
    out_dir = job / FRAMES
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir()
    W, H = 96, 54
    r = subprocess.run([ffprobe(), "-v", "error", "-skip_frame", "nokey", "-select_streams", "v:0",
                        "-show_entries", "frame=pts_time", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, **HIDDEN)
    times = []
    for line in r.stdout.split():
        try:
            times.append(float(line.strip(",")))
        except ValueError:
            pass
    raw = subprocess.run([ffmpeg(), "-v", "error", "-nostdin", "-skip_frame", "nokey", "-i", str(video),
                          "-vf", f"scale={W}:{H},format=gray", "-fps_mode", "passthrough", "-f", "rawvideo", "-"],
                         capture_output=True, **HIDDEN).stdout
    smalls = np.frombuffer(raw, dtype=np.uint8)[:len(raw) // (W * H) * W * H].reshape(-1, H, W).astype(np.int16)
    n = min(len(times), len(smalls))
    total = times[n - 1] if n else 0
    out, saved, prev, pend_t = [], None, None, None
    for k in range(n):
        t, small = times[k], smalls[k]
        differs = saved is None or (np.abs(small - saved) > 24).mean() > 0.03
        stable = prev is not None and (np.abs(small - prev) > 24).mean() < 0.005
        prev = small
        if not differs:
            pend_t = None
            continue
        pend_t = t if pend_t is None else pend_t
        # видео или прокрутка: картинка не успокаивается — всё равно сохраняем, но не чаще раза в 30 с
        if not (saved is None or stable or t - pend_t >= 30):
            continue
        name = f"{len(out) + 1:03d}.jpg"
        subprocess.run([ffmpeg(), "-v", "error", "-nostdin", "-y", "-ss", f"{t:.3f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale='min(1280,iw)':-2", "-q:v", "4", str(out_dir / name)],
                       capture_output=True, **HIDDEN)
        if not (out_dir / name).exists():
            continue
        out.append({"t": round(to_record(pend_t, vmap), 1), "file": f"{FRAMES}/{name}"})
        saved, pend_t = small, None
        if total:
            progress(90 + 10 * t / total)
        if len(out) >= MAX_FRAMES:
            break
    if not out:
        shutil.rmtree(out_dir, ignore_errors=True)
    return out
