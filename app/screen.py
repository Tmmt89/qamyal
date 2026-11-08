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

from sysdeps import HIDDEN, find_program, screen_encoders, screen_inputs

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
    scale = f"scale=-2:'min({h},ih)'," if h else ""
    out = []
    for inp, pre in screen_inputs(fps, monitor):
        for enc, pix in screen_encoders(q, fps):
            vf = ",".join(x for x in (pre, scale.rstrip(","), f"format={pix}") if x)
            out.append(inp + ["-vf", vf] + enc)
    return out


def _probe(args: list) -> bool:
    """Полсекунды пробной съёмки: работают ли этот способ и кодер на этом компьютере."""
    try:
        r = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-nostdin", *args,
                            "-frames:v", "5", "-f", "null", "-"],
                           capture_output=True, timeout=20, **HIDDEN)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def pick(quality: str, monitor: int) -> list:
    key = (quality, monitor)
    if key not in _works:
        _works[key] = next((a for a in _variants(quality, monitor) if _probe(a)), None)
    if not _works[key]:
        raise RuntimeError("не удалось начать съёмку экрана")
    return _works[key]


class ScreenRecorder:
    """Пишет экран в rec-….screen-N.mkv рядом со звуком; список кусков — в rec-….screen.json."""

    def __init__(self, base: Path, quality: str, monitor: int):
        self.base, self.quality, self.monitor = base, quality, monitor
        self.args = pick(quality, monitor)
        self.segments = []
        self.proc = None
        self.error = ""
        self.lock = threading.Lock()

    @property
    def meta_path(self) -> Path:
        return self.base.with_suffix(".screen.json")

    def _save(self):
        self.meta_path.write_text(json.dumps({"quality": self.quality, "segments": self.segments},
                                             ensure_ascii=False), encoding="utf-8")

    def start(self, timeout: float = 8.0) -> None:
        """Новый кусок. Возвращается, когда ffmpeg выдал первые кадры, — звук начнётся уже после картинки."""
        with self.lock:
            if self.proc:
                return
            f = self.base.with_name(f"{self.base.stem}.screen-{len(self.segments) + 1}.mkv")
            a = self.args
            log = self.base.with_suffix(".screen.log")
            with open(log, "ab") as err:          # ошибки ffmpeg — в файл: труба за час записи могла бы переполниться
                p = subprocess.Popen([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *a,
                                      "-progress", "pipe:1", "-stats_period", "0.1", str(f)],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, **HIDDEN)
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

            threading.Thread(target=watch, daemon=True).start()
            if not first.wait(timeout) or p.poll() is not None:
                self._kill(p)
                err = log.read_text("utf-8", "replace").strip()
                f.unlink(missing_ok=True)
                raise RuntimeError("экран не записывается" + (f": {err.splitlines()[-1]}" if err else ""))
            self.proc = p
            self.segments.append(seg)
            self._save()

    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self) -> None:
        """Закрыть кусок: «q» — ffmpeg дописывает файл как положено."""
        with self.lock:
            p, self.proc = self.proc, None
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
        name = META if f.suffix == ".json" else f.name.split(".screen-")[1]     # «1.mkv»
        shutil.move(str(f), str(d / name))
    meta = json.loads((d / META).read_text(encoding="utf-8"))
    for s in meta["segments"]:
        s["file"] = s["file"].split(".screen-")[1]
    (d / META).write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return True


def duration(path: Path) -> float:
    r = subprocess.run([find_program("ffprobe") or ffmpeg().replace("ffmpeg", "ffprobe"), "-v", "error",
                        "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, **HIDDEN)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


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
    audio, sr = sf.read(str(wav), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    tl = timeline(segs, anchors, len(audio) / sr)
    track = np.zeros(int(sum(s["dur"] for s in segs) * sr) + 1, dtype=np.float32)
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
    отличается от последнего сохранённого и уже не меняется (анимация перехода закончилась)."""
    import av
    video = job / VIDEO
    out_dir = job / FRAMES
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir()
    out = []
    with av.open(str(video)) as c:
        st = c.streams.video[0]
        st.codec_context.skip_frame = "NONKEY"
        total = float(st.duration * st.time_base) if st.duration else 0
        saved = prev = None
        pend_t = None
        for frame in c.decode(st):
            t = float(frame.time or 0)
            small = frame.reformat(width=96, height=54, format="gray").to_ndarray().astype(np.int16)
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
            img = frame.to_image()
            if img.width > 1280:
                img = img.resize((1280, round(img.height * 1280 / img.width)))
            rt = round(to_record(pend_t, vmap), 1)
            name = f"{len(out) + 1:03d}.jpg"
            img.save(out_dir / name, quality=80)
            out.append({"t": rt, "file": f"{FRAMES}/{name}"})
            saved, pend_t = small, None
            if total:
                progress(90 + 10 * t / total)
            if len(out) >= MAX_FRAMES:
                break
    if not out:
        shutil.rmtree(out_dir, ignore_errors=True)
    return out
