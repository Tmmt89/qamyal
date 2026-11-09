"""Фоновый обработчик очереди. Его запускает окно программы; работает, пока есть необработанные записи."""
import logging
import os
import time
import traceback
from pathlib import Path

import sysdeps
from sysdeps import keep_awake, low_priority
from common import (JOBS, LOCK, LOG, PAUSE, SERVICES, add_project, fmt_time, job_id, load_settings, pending_jobs, pid_alive,
                    projects_of, read_job, read_json, rename_job_dir, set_projects, update_job, worker_pid,
                    write_job, write_json)

log = logging.getLogger("worker")


def pause_requested() -> bool:
    """Окно программы ставит паузу на время живой расшифровки (в файле — его PID)."""
    try:
        pid = int(PAUSE.read_text())
    except (OSError, ValueError):
        return False
    if pid_alive(pid):
        return True
    PAUSE.unlink(missing_ok=True)
    return False


def write_draft_txt(path: Path, turns: list) -> None:
    path.write_text("\n".join(f"[{fmt_time(t['s'])}] {t['who']}: {t['text']}" for t in turns) + "\n",
                    encoding="utf-8")


def notify(title: str, text: str, target: Path) -> None:
    try:
        sysdeps.notify(title, text, target, Path(__file__).with_name("icon") / "qamyal-256.png")
    except Exception as e:  # noqa: BLE001 — уведомление не должно ломать обработку
        log.warning("уведомление не показано: %s", e)


def process(d: Path, s: dict) -> None:
    import asr
    import editor
    import render
    import voices

    drafts = d / "черновики"
    drafts.mkdir(exist_ok=True)
    wav, mp3 = drafts / "audio16k.wav", d / "запись.mp3"
    cache = {}

    def audio():
        if "a" not in cache:
            cache["a"] = asr.load_wav(wav) if wav.exists() else asr.decode(mp3)
        return cache["a"]

    def run(key, fn):
        job = read_job(d)
        if key in job.get("done", []):
            return
        attempts = job.setdefault("attempts", {})
        attempts[key] = attempts.get(key, 0) + 1
        if attempts[key] > 3:
            raise RuntimeError("этап несколько раз прерывался — нажмите «Повторить»")
        job.update(status="working", stage=key, progress=0, error="", paused=False)
        write_job(d, job)
        last = [0.0]

        def progress(p):
            if pause_requested():
                update_job(d, paused=True)
                while pause_requested():
                    time.sleep(1)
                update_job(d, paused=False)
            if time.time() - last[0] > 2:
                last[0] = time.time()
                update_job(d, progress=int(p))

        t = time.time()
        log.info("%s: %s", d.name, key)
        fn(progress)
        job = read_job(d)
        job.setdefault("done", []).append(key)
        job.setdefault("times", {})[key] = round(time.time() - t)
        job["progress"] = 100
        write_job(d, job)

    def prepare(progress):
        src = next(p for p in drafts.iterdir() if p.stem == "исходник")
        update_job(d, duration=asr.prepare(src, wav, mp3))

    def video(progress):
        """Запись экрана: куски картинки + звук → видео.mp4 и карта «время записи → время видео»."""
        import screen
        if not (drafts / "экран" / screen.META).exists():
            return
        job = read_job(d)
        anchors = job.get("rec_anchors") or []
        if not anchors:            # восстановленная запись: считаем, что звук начался с первого кадра
            meta = read_json(drafts / "экран" / screen.META, {})
            v0 = next((x["v0"] for x in meta.get("segments", []) if x.get("v0")), 0)
            anchors = [[0.0, v0]]
        try:
            vmap = screen.mux(d, wav, anchors, progress)
        except Exception as e:  # noqa: BLE001 — без видео расшифровка всё равно нужна; куски остаются в черновиках
            log.warning("видео с экрана не собрано: %s", e)
            update_job(d, video_error=str(e)[:300])
            return
        update_job(d, video_map=vmap)
        if (d / screen.VIDEO).exists():
            try:
                update_job(d, frames=screen.keyframes(d, vmap, progress))
            except Exception as e:  # noqa: BLE001 — без кадров итог всё равно нужен
                log.warning("кадры экрана не выбраны: %s", e)

    def gigaam(progress):
        write_json(drafts / "gigaam.json", asr.run_gigaam(audio(), s["threads"], progress))

    def is_call():
        """Запись диктофона в режиме «Созвон»: левый канал — микрофон, правый — собеседники."""
        return read_job(d).get("recorded") == "both" and any(p.stem == "исходник" for p in drafts.iterdir())

    def skype_diar():
        """Созвон: кто говорит — по журналу сервиса, а не по голосу. Skype для бизнеса пишет skype.jsonl
        (Lync SDK), остальные — говорящие.jsonl (расширение Chrome, разведчик окон) в том же виде."""
        import skype
        job = read_job(d)
        if job.get("recorded") not in ("both", "system"):
            return None
        log = drafts / ("skype.jsonl" if job.get("service") in (None, "", "skype") else "говорящие.jsonl")
        tl = skype.timeline(log, job.get("rec_anchors"), job.get("duration") or 0)
        src = next((p for p in drafts.iterdir() if p.stem == "исходник"), None)
        if not tl or src is None:
            return None
        if is_call():
            mic, system = asr.decode_channel(src, 0), asr.decode_channel(src, 1)
        else:
            mic, system = None, audio()
        res, names = skype.diarize(mic, system, *tl, s["user_name"], sorted(voices.load_db()))
        write_json(drafts / "голоса-skype.json", {str(k): v for k, v in names.items()})
        update_job(d, num_speakers=len(names), skype_people={v["name"]: v["uri"] for v in names.values()})
        return res

    def diar(progress):
        # разметка всегда автоматическая (она дробит людей на куски); известное число людей
        # учитываем при склейке кусков по голосу — так точнее, чем заставлять разметку делить на N
        res = skype_diar()
        if res is None and is_call():
            src = next(p for p in drafts.iterdir() if p.stem == "исходник")
            res = asr.run_diar_call(asr.decode_channel(src, 0), asr.decode_channel(src, 1), s["threads"],
                                    s["diar_threshold"], progress)
        elif res is None:
            res = asr.run_diar(audio(), s["threads"], s["diar_threshold"], progress)
        write_json(drafts / "голоса-сырые.json", res)   # исходная разметка: пересчёт людей идёт от неё
        write_json(drafts / "голоса.json", res)

    def recognize(progress):
        job = read_job(d)
        call = is_call()
        dia = read_json(drafts / "голоса-сырые.json") or read_json(drafts / "голоса.json", [])
        by_skype = read_json(drafts / "голоса-skype.json")
        if by_skype:
            # имена известны точно: склеивать и угадывать по голосу нечего, отпечатки — для обучения
            write_json(drafts / "голоса.json", dia)
            write_json(drafts / "голоса-отпечатки.json", voices.cluster_embeddings(audio(), dia))
            labels = asr.label_speakers(dia)
            write_json(drafts / "голоса-узнаны.json",
                       {labels[int(k)]: {"name": v["name"], "score": 1.0, "spk": int(k), "how": "skype"}
                        for k, v in by_skype.items() if int(k) in labels})
            return
        keep = {0} if call and any(x["spk"] == 0 for x in dia) else set()
        n = int(job.get("num_speakers") or 0)
        target = max(1, n - len(keep)) if n else 0
        if target and len({x["spk"] for x in dia} - keep) < target:
            # разметка нашла меньше голосов, чем людей на самом деле (похожие голоса слились) —
            # заставляем её делить ровно на нужное число
            if call:
                src = next(p for p in drafts.iterdir() if p.stem == "исходник")
                dia = asr.run_diar_call(asr.decode_channel(src, 0), asr.decode_channel(src, 1), s["threads"],
                                        s["diar_threshold"], progress, target)
            else:
                dia = asr.run_diar(audio(), s["threads"], s["diar_threshold"], progress, target)
        clusters = voices.cluster_embeddings(audio(), dia)
        # склеиваем куски одного голоса (до заданного числа людей, если оно известно) и мелкие обрывки
        dia, clusters = voices.merge_similar(dia, clusters, keep, target=target)
        dia, clusters = voices.merge_small(dia, clusters, keep, target=target)
        write_json(drafts / "голоса.json", dia)
        write_json(drafts / "голоса-отпечатки.json", clusters)
        labels = asr.label_speakers(dia)
        found = voices.match({k: v for k, v in clusters.items() if not (call and int(k) == 0)}, labels,
                             exclusive=bool(n), exclude={s["user_name"]} if keep else set())
        if call and any(x["spk"] == 0 for x in dia):
            found = {k: v for k, v in found.items() if v["name"] != s["user_name"]}
            found[labels[0]] = {"name": s["user_name"], "score": 1.0, "spk": 0, "how": "mic"}
        write_json(drafts / "голоса-узнаны.json", found)

    def whisper(progress):
        from components import whisper_ready
        segs = asr.run_whisper(audio(), s["threads"], s["whisper_beam"], progress) \
            if read_job(d).get("whisper", True) and whisper_ready() else []
        write_json(drafts / "whisper.json", segs)

    def edit(progress):
        dia = read_json(drafts / "голоса.json", [])
        a = asr.to_turns(read_json(drafts / "gigaam.json", []), dia)
        b = asr.to_turns(read_json(drafts / "whisper.json", []), dia)
        write_draft_txt(drafts / "черновик GigaAM.txt", a)
        if b:
            write_draft_txt(drafts / "черновик Whisper.txt", b)
        job = read_job(d)
        mode = job.get("editor", s["editor"])
        hints = voices.describe(read_json(drafts / "голоса-узнаны.json", {}))
        if SERVICES.get(job.get("service") or ""):
            hints = f"Это созвон через {SERVICES[job['service']]}.\n{hints}".strip()
        res = editor.edit(d, job["name"], a, b, {**s, "editor": mode}, progress, hints) \
            if mode in ("claude", "codex", "openai") else editor.plain(a, read_json(drafts / "голоса-узнаны.json", {}))
        write_json(drafts / "итог-правка.json", res)

    def finish(progress):
        job = read_job(d)
        res = read_json(drafts / "итог-правка.json")
        res["title"] = res.get("title") or job["name"]
        res.update(date=job.get("date", ""), duration=job.get("duration", 0), source=job.get("source"),
                   marks=job.get("marks", []))
        # проекты: если пользователь задал вручную — его, иначе те, что определил ИИ (их может быть несколько)
        about = res.pop("project_about", None)
        if job.get("project_manual"):
            set_projects(res, projects_of(job))
        else:
            set_projects(res, projects_of(res))
            for p in res["projects"]:
                add_project(p, about.get(p, "") if isinstance(about, dict) else (about or ""))
        update_job(d, projects=res["projects"], project=res["project"])
        dia = read_json(drafts / "голоса.json", [])
        mapping = voices.full_mapping(dia, res["turns"], read_json(drafts / "голоса-узнаны.json", {}))
        write_json(drafts / "кто-есть-кто.json", {str(k): v for k, v in mapping.items()})
        res["stats"] = voices.talk_stats(dia, mapping, asr.label_speakers(dia))
        write_json(drafts / "волна.json", asr.peaks(audio()))
        render.render(d, res)
        clusters = read_json(drafts / "голоса-отпечатки.json", {})
        if clusters and mapping:
            learned = voices.learn(job_id(d), res["title"], clusters, mapping, dia)
            update_job(d, learned=learned)
        if wav.exists():
            cache.pop("a", None)
            wav.unlink()

    for key, fn in (("prepare", prepare), ("video", video), ("gigaam", gigaam), ("diar", diar), ("voices", recognize),
                    ("whisper", whisper), ("edit", edit), ("render", finish)):
        run(key, fn)
    job = update_job(d, status="done", stage="", finished=time.time())
    res = read_json(drafts / "итог.json", {})
    if res.get("title"):
        d = rename_job_dir(d, res["title"])          # папка — по дате и смыслу разговора
    log.info("%s: готово", d.name)
    if s.get("notify", True):
        notify("Расшифровка готова", res.get("title") or job["name"], render.outputs(d)["html"])


def main() -> None:
    JOBS.mkdir(exist_ok=True)
    # два обработчика на одной записи портят её job.json (09.11: диктофон и окно запустили их в одну секунду) —
    # замок системы, а не проверка «есть ли файл»: её два процесса проходят одновременно
    if not sysdeps.single_instance(JOBS / ".worker.mutex"):
        return
    LOCK.write_text(str(os.getpid()))
    logging.basicConfig(filename=LOG, encoding="utf-8", level=logging.INFO,
                        format="%(asctime)s %(message)s")
    low_priority()
    keep_awake(True)
    try:
        while True:
            jobs = pending_jobs()
            if not jobs:
                break
            d, _ = jobs[0]
            try:
                process(d, load_settings())
            except Exception as e:  # noqa: BLE001 — любая ошибка задания не должна ронять очередь
                log.error("%s: %s\n%s", d.name, e, traceback.format_exc())
                update_job(d, status="error", error=str(e)[:400], paused=False)
    finally:
        keep_awake(False)
        try:
            if int(LOCK.read_text()) == os.getpid():
                LOCK.unlink()
        except (OSError, ValueError):
            pass


if __name__ == "__main__":
    main()
