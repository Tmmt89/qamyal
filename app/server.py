"""Локальный сервер окна программы: страницы интерфейса + API (только 127.0.0.1)."""
import os
import re
import shutil
import threading
import time
from pathlib import Path

import bottle
from bottle import request, response, static_file

import editor
import render
from common import (APP, GLOSSARY, INCOMING, JOBS, SERVICES, STAGE_LABEL, TASKS_STATE, backup, codex_status, create_job, eta,
                    versions_dir,
                    find_codex, find_job, parse_time, projects_of, set_projects,
                    fmt_time, job_id, list_jobs, load_settings, pending_jobs, read_glossary, read_job,
                    read_json, rename_job_dir, save_settings, spawn_worker, task_key, update_job, worker_pid,
                    write_job, write_json, add_project, load_projects, save_projects)
from dictate import Dictation
from recorder import Recorder, devices
from sysdeps import IS_WIN, open_console, open_path, screen_monitors, screen_supported

WEB = APP / "web"
UI_PROFILE = APP / ".ui-profile"       # профиль Chrome для окон программы (Windows), тот же, что в app.py
bottle.BaseRequest.MEMFILE_MAX = 64 * 1024 * 1024
app = bottle.Bottle()
rec = Recorder()
dictation = Dictation()
last_ping = [time.time()]
_cache = {}
_spawned = [0.0]
learning = {"running": False, "done": 0, "total": 0, "message": ""}


# ---------- помощники ----------

def cached_json(path: Path, default=None):
    """Чтение JSON с кэшем по времени изменения файла (список записей опрашивается часто)."""
    try:
        mt = path.stat().st_mtime
    except OSError:
        return default
    hit = _cache.get(path)
    if hit and hit[0] == mt:
        return hit[1]
    data = read_json(path, default)
    _cache[path] = (mt, data)
    return data


def job_or_404(jid: str) -> Path:
    d = find_job(jid)
    if not d:
        bottle.abort(404, "Запись не найдена")
    return d


def ensure_worker():
    if pending_jobs() and not worker_pid() and time.time() - _spawned[0] > 15:
        _spawned[0] = time.time()
        spawn_worker()


def summary(d: Path, j: dict) -> dict:
    res = cached_json(d / "черновики" / "итог.json", {}) if j.get("status") == "done" else {}
    st = j.get("status")
    return {
        "id": job_id(d), "name": j.get("name", d.name), "title": res.get("title") or j.get("name", d.name),
        "date": j.get("date", ""), "ts": j.get("ts") or j.get("added", 0), "duration": j.get("duration", 0),
        "status": st, "stage": j.get("stage", ""), "stage_label": STAGE_LABEL.get(j.get("stage", ""), ""),
        "progress": j.get("progress", 0), "eta": eta(j) if st == "working" else 0,
        "paused": j.get("paused", False), "error": j.get("error", ""),
        "participants": res.get("participants", []), "lead": (res.get("summary") or [""])[0],
        "recorded": j.get("recorded", ""), "marks": len(j.get("marks", [])), "screen": j.get("screen", ""),
        "service": SERVICES.get(j.get("service") or "", ""),
        "projects": projects_of(j) or projects_of(res),
        "tasks": len(res.get("tasks") or []),
    }


def result_of(d: Path) -> dict:
    return read_json(d / "черновики" / "итог.json")


def save_result(d: Path, res: dict, relearn: bool = True, what: str = "") -> None:
    import voices
    from asr import label_speakers
    backup(d, what)
    dia = read_json(d / "черновики" / "голоса.json", [])
    if dia and res.get("turns"):                 # «кто сколько говорил» — по новым именам
        res["stats"] = voices.talk_stats(dia, voices.full_mapping(dia, res["turns"], read_json(d / "черновики" / "голоса-узнаны.json", {})), label_speakers(dia))
    render.render(d, res)
    _cache.pop(d / "черновики" / "итог.json", None)
    if relearn:
        threading.Thread(target=relearn_job, args=(d,), daemon=True).start()


def relearn_job(d: Path) -> None:
    """После правки имён — заново запоминаем голоса этой записи (если есть отпечатки)."""
    import voices
    res = result_of(d) or {}
    dia = read_json(d / "черновики" / "голоса.json", [])
    clusters = read_json(d / "черновики" / "голоса-отпечатки.json")
    if not (res.get("turns") and dia and clusters):
        return
    mapping = voices.full_mapping(dia, res["turns"], read_json(d / "черновики" / "голоса-узнаны.json", {}))
    write_json(d / "черновики" / "кто-есть-кто.json", {str(k): v for k, v in mapping.items()})
    voices.learn(job_id(d), res.get("title", d.name), clusters, mapping, dia)


def body() -> dict:
    return request.json or {}


# ---------- страницы ----------

@app.get("/")
@app.get("/mini")          # мини-окно: свой адрес — у Chrome свой запомненный размер окна, не как у основного
def index():
    return static_file("index.html", root=str(WEB))


@app.get("/static/<path:path>")
def static(path):
    resp = static_file(path, root=str(WEB))
    resp.set_header("Cache-Control", "no-cache")
    return resp


@app.get("/media/<jid>")
def media(jid):
    d = job_or_404(jid)
    return static_file("запись.mp3", root=str(d), mimetype="audio/mpeg")


@app.get("/frame/<jid>/<name>")
def frame(jid, name):
    """Кадр записи экрана (папка «кадры» в папке записи)."""
    d = job_or_404(jid)
    resp = static_file(name, root=str(d / "кадры"), mimetype="image/jpeg")
    resp.set_header("Cache-Control", "max-age=86400")
    return resp


# ---------- общее состояние ----------

@app.get("/api/state")
def state():
    last_ping[0] = time.time()
    ensure_worker()
    jobs = list_jobs()
    work = [summary(d, j) for d, j in jobs if j.get("status") in ("queued", "working")]
    work.sort(key=lambda x: (x["status"] != "working", x["ts"]))
    import components
    st = rec.status()
    st.pop("live_segments", None)
    s = load_settings()
    components.claude_appeared(s)
    dl = components.running()
    open_tasks = 0
    done_map = read_json(TASKS_STATE, {})
    for d, j in jobs:
        if j.get("status") == "done":
            for t in (cached_json(d / "черновики" / "итог.json", {}) or {}).get("tasks") or []:
                who = t.get("who", "") if isinstance(t, dict) else ""
                what = t.get("what", "") if isinstance(t, dict) else str(t)
                if s["user_name"] and s["user_name"].lower() in who.lower() and not done_map.get(task_key(job_id(d), what)):
                    open_tasks += 1
    return {"work": work, "worker": bool(worker_pid()), "rec": st, "my_open_tasks": open_tasks,
            "errors": sum(1 for _, j in jobs if j.get("status") == "error"),
            "user": s["user_name"], "editor": s["editor"], "theme": s.get("theme", "system"),
            "lang": s.get("lang", "ru"), "speech": components.speech_ready(),
            "download": {**dl[0], "more": len(dl) - 1} if dl else None}


# ---------- о программе ----------

@app.get("/api/about")
def about():
    """Версия, статистика по всем записям, модели и компьютер — для карточки «О программе»."""
    import platform
    import components
    from sysdeps import machine_info, os_name
    jobs = list_jobs()
    done = [(d, j) for d, j in jobs if j.get("status") == "done"]
    words, talk, longest = 0, {}, None
    for d, j in done:
        res = cached_json(d / "черновики" / "итог.json", {}) or {}
        words += sum(len(t.get("text", "").split()) for t in res.get("turns") or [])
        for x in res.get("stats") or []:
            if x.get("who") and not x["who"].startswith("Спикер") and x["who"] != "?":
                talk[x["who"]] = talk.get(x["who"], 0) + x.get("sec", 0)
        if j.get("duration") and (not longest or j["duration"] > longest[1].get("duration", 0)):
            longest = (d, j, res)
    import voices
    all_tasks = tasks()["tasks"]
    first = min((j.get("ts") or j.get("added") or 0 for _, j in jobs), default=0)
    newest = max(p.stat().st_mtime for p in list(APP.glob("*.py")) + list((APP / "web").glob("*.*")))
    return {
        "version": time.strftime("%d.%m.%Y", time.localtime(newest)),
        "stats": {
            "jobs": len(jobs), "done": len(done),
            "hours": sum(j.get("duration") or 0 for _, j in jobs) / 3600,
            "work_hours": sum(sum((j.get("times") or {}).values()) for _, j in done) / 3600,
            "words": words, "first": first,
            "voices": len(voices.load_db()), "projects": len(load_projects()),
            "tasks": len(all_tasks), "tasks_done": sum(1 for t in all_tasks if t["done"]),
            "talkers": [{"who": k, "sec": v} for k, v in sorted(talk.items(), key=lambda x: -x[1])[:3]],
            "longest": {"id": job_id(longest[0]), "title": longest[2].get("title") or longest[1].get("name", ""),
                        "duration": longest[1]["duration"]} if longest else None,
        },
        "models": {"whisper": components.whisper_model() if components.whisper_ready() else "",
                   "speech": components.speech_ready(), "editor": load_settings()["editor"]},
        "machine": {**machine_info(), "os": os_name(), "python": platform.python_version()},
        "paths": {"root": str(APP.parent), "jobs": str(JOBS)},
    }


# ---------- обновление (Mac): новая версия с GitHub по кнопке ----------

@app.get("/api/update")
def update_get():
    import update
    return update.check(force=bool(request.query.get("now")))


@app.post("/api/update")
def update_start():
    import components
    import update
    if rec.state != "idle" or worker_pid() or components.running():
        bottle.abort(409, "Сейчас идёт запись, обработка или загрузка — обновите, когда закончится")
    try:
        update.start()
    except RuntimeError as e:
        bottle.abort(409, str(e))
    return {"ok": True}


# ---------- что докачивается по кнопке ----------

@app.get("/api/components")
def components_get():
    import components
    return components.status()


@app.post("/api/components/<cid:re:speech|whisper|claude|codex>")
def components_start(cid):
    import components
    try:
        components.start(cid, str(body().get("model", "")))
    except RuntimeError as e:
        bottle.abort(409, str(e))
    return components.status()


@app.post("/api/components/whisper/<action:re:use|delete>")
def whisper_variant(action):
    """Выбрать скачанный вариант Whisper или удалить ненужный."""
    import components
    key = str(body().get("model", ""))
    try:
        (components.use_whisper if action == "use" else components.delete_whisper)(key)
    except RuntimeError as e:
        bottle.abort(409, str(e))
    return components.status()


# ---------- записи ----------

@app.get("/api/jobs")
def jobs():
    return {"jobs": [summary(d, j) for d, j in list_jobs()]}


@app.post("/api/upload")
def upload():
    s = load_settings()
    INCOMING.mkdir(parents=True, exist_ok=True)
    stamps = request.forms.getall("lastModified")
    made = []
    for i, f in enumerate(request.files.getall("files")):
        name = f.raw_filename or f.filename
        tmp = INCOMING / f"up-{time.time_ns()}{Path(name).suffix.lower()}"
        f.save(str(tmp))
        try:
            when = float(stamps[i]) / 1000 if i < len(stamps) else None
        except ValueError:
            when = None
        made.append(job_id(create_job(tmp, s, move=True, name=Path(name).stem, when=when)))
    ensure_worker()
    return {"created": made}


@app.get("/api/job/<jid>")
def job(jid):
    import voices
    from asr import label_speakers
    d = job_or_404(jid)
    j = read_job(d)
    out = {"job": summary(d, j), "marks": j.get("marks", []), "times": j.get("times", {})}
    if request.query.get("lite"):
        return out
    res = result_of(d)
    out["result"] = res
    out["live"] = read_json(d / "черновики" / "живая.json", [])
    out["qa"] = read_json(d / "черновики" / "вопросы.json", [])
    out["has_audio"] = (d / "запись.mp3").exists()
    out["has_video"] = (d / "видео.mp4").exists()
    if out["has_video"] and res:
        import render
        out["frames"] = [{"t": f["t"], "src": f"/frame/{jid}/{f['file'].rsplit('/', 1)[-1]}",
                          "caption": render.shot_caption(f, res)}
                         for f in j.get("frames") or [] if (d / f["file"]).exists()]
    dia = read_json(d / "черновики" / "голоса.json", [])
    if res and dia:
        mapping = voices.full_mapping(dia, res["turns"], read_json(d / "черновики" / "голоса-узнаны.json", {}))      # по текущим именам (после правок)
        labels = label_speakers(dia)
        strip = []
        for seg in dia:
            who = mapping.get(seg["spk"]) or labels.get(seg["spk"], "?")
            if strip and strip[-1]["who"] == who and seg["s"] - strip[-1]["e"] < 1.0:
                strip[-1]["e"] = seg["e"]
            else:
                strip.append({"s": seg["s"], "e": seg["e"], "who": who})
        out["speakers"] = strip
        if not res.get("stats"):
            res["stats"] = voices.talk_stats(dia, mapping, labels)
    out["recognized"] = read_json(d / "черновики" / "голоса-узнаны.json", {})
    out["versions"] = len(list(versions_dir(d).glob("*.json")))
    out["projects"] = [p["name"] for p in load_projects()]
    out["num_speakers"] = j.get("num_speakers")
    out["known_voices"] = sorted(voices.load_db())
    if res:
        done_map = read_json(TASKS_STATE, {})
        out["tasks_state"] = []
        for t in res.get("tasks") or []:
            key = task_key(jid, t.get("what", "") if isinstance(t, dict) else str(t))
            out["tasks_state"].append({"key": key, "done": bool(done_map.get(key))})
    return out


@app.get("/api/job/<jid>/peaks")
def peaks(jid):
    import asr
    d = job_or_404(jid)
    p = d / "черновики" / "волна.json"
    data = read_json(p)
    if data is None and (d / "запись.mp3").exists():
        data = asr.peaks(asr.decode(d / "запись.mp3"))
        write_json(p, data)
    return {"peaks": data or []}


@app.post("/api/job/<jid>/turns")
def save_turns(jid):
    d = job_or_404(jid)
    res = result_of(d)
    turns = body().get("turns")
    if not res or not isinstance(turns, list):
        bottle.abort(400, "Нет текста")
    res["turns"] = [{"t": float(t["t"]), "who": str(t["who"]).strip() or "?", "text": str(t["text"]).strip()}
                    for t in turns if str(t.get("text", "")).strip()]
    save_result(d, res, what="правка текста вручную")
    return {"ok": True}


# падежи простых имён: окончание → (основа без него, окончания им., род., дат., вин., твор., предл.)
_CASES = [("ий", ["ий", "ия", "ию", "ия", "ием", "ии"]), ("ь", ["ь", "я", "ю", "я", "ем", "е"]),
          ("й", ["й", "я", "ю", "я", "ем", "е"]),
          ("ия", ["ия", "ии", "ии", "ию", "ией", "ии"]), ("а", ["а", "ы", "е", "у", "ой", "е"]),
          ("я", ["я", "и", "е", "ю", "ей", "е"])]
_CONS = ["", "а", "у", "а", "ом", "е"]
_FLEET = {"Лев": ("Л", ["ев", "ьва", "ьву", "ьва", "ьвом", "ьве"]),       # беглая гласная
          "Павел": ("Пав", ["ел", "ла", "лу", "ла", "лом", "ле"])}


def name_forms(name: str):
    """(основа, окончания по падежам) для однословного русского имени; None — склонять не берёмся."""
    if name in _FLEET:
        return _FLEET[name]
    if not re.fullmatch(r"[А-ЯЁ][а-яё]+", name):
        return None
    for end, forms in _CASES:
        if name.endswith(end):
            stem = name[:-len(end)]
            if end == "а" and stem[-1:] in "гкхжчшщ":        # Ольга → Ольги, Наташа → Наташи
                forms = ["а", "и", "е", "у", "ой", "е"]
            return stem, forms
    if name[-1] in "бвгджзклмнпрстфхцчшщ":
        return name, _CONS
    return None


def rename_in_texts(res: dict, old: str, new: str) -> None:
    """Старое имя в кратком содержании, решениях и задачах — на новое, в том же падеже:
    «Урала» → «Рафаэля», «Уралом» → «Рафаэлем». «Спикер 4» в любом падеже — на новое имя как есть."""
    m = re.fullmatch(r"Спикер (\d+)", old)
    fo, fn = name_forms(old), name_forms(new)
    if m:
        rx, sub = re.compile(rf"(?<!\w)Спикер\w*\s+{m.group(1)}(?!\d)"), new
    elif fo:
        stem, ends = fo
        alts = sorted({e for e in ends}, key=len, reverse=True)
        rx = re.compile(rf"(?<!\w){re.escape(stem)}({'|'.join(map(re.escape, alts))})(?!\w)")

        def sub(mm):
            if not fn:
                return new
            forms = {fn[0] + fn[1][k] for k, e in enumerate(ends) if e == mm.group(1)}
            return forms.pop() if len(forms) == 1 else new   # падеж не ясен («Анне» — дат. или предл.) — как есть
    else:
        rx, sub = re.compile(rf"(?<!\w){re.escape(old)}(?!\w)"), new
    for key in ("summary", "decisions"):
        res[key] = [rx.sub(sub, x) for x in res.get(key) or []]
    for t in res.get("tasks") or []:
        if isinstance(t, dict):
            for k in ("who", "what"):
                if isinstance(t.get(k), str):
                    t[k] = rx.sub(sub, t[k])


def merge_stats(res: dict) -> None:
    tot = {}
    for x in res.get("stats") or []:
        tot[x["who"]] = tot.get(x["who"], 0) + x["sec"]
    res["stats"] = [{"who": k, "sec": v} for k, v in sorted(tot.items(), key=lambda x: -x[1])]


@app.post("/api/job/<jid>/rename")
def rename(jid):
    """Все реплики одного участника — другому имени (так же сливаются раздробленные «спикеры»)."""
    d = job_or_404(jid)
    res = result_of(d)
    old, new = body().get("from", ""), body().get("to", "").strip()
    if not res or not new:
        bottle.abort(400, "Нужно новое имя")
    for t in res["turns"]:
        if t["who"] == old:
            t["who"] = new
    for x in res.get("stats") or []:
        if x["who"] == old:
            x["who"] = new
    merge_stats(res)
    rename_in_texts(res, old, new)
    save_result(d, res, what=f"«{old}» → «{new}»")
    people = read_job(d).get("skype_people") or {}
    if old in people and not new.startswith("Спикер"):
        import skype
        skype.remember(people[old], new)          # в следующих созвонах этот участник Skype — сразу под новым именем
        people[new] = people.pop(old)
        update_job(d, skype_people=people)
    return {"ok": True}


@app.post("/api/job/<jid>/turn")
def turn_speaker(jid):
    """Сменить говорящего у одной реплики."""
    d = job_or_404(jid)
    res = result_of(d)
    b = body()
    i, who = int(b.get("i", -1)), str(b.get("who", "")).strip()
    if not res or not who or not 0 <= i < len(res["turns"]):
        bottle.abort(400, "Нет такой реплики")
    old = res["turns"][i]["who"]
    res["turns"][i]["who"] = who
    save_result(d, res, what=f"реплика {fmt_time(res['turns'][i]['t'])}: «{old}» → «{who}»")
    if not who.startswith("Спикер"):
        threading.Thread(target=sample_turn, args=(d, res, i, who), daemon=True).start()
    return {"ok": True}


def sample_turn(d: Path, res: dict, i: int, who: str) -> None:
    """Реплику подписали вручную — её звук становится подтверждённым образцом голоса этого человека."""
    import asr
    import voices
    t = res["turns"][i]
    end = res["turns"][i + 1]["t"] if i + 1 < len(res["turns"]) else t["t"] + 20
    dur = min(30.0, max(0.0, end - t["t"]))
    if dur < 2 or not (d / "запись.mp3").exists():
        return
    try:
        voices.add_sample(who, job_id(d), res.get("title", ""), asr.decode_range(d / "запись.mp3", t["t"], dur), t["t"])
    except Exception:  # noqa: BLE001 — образец необязателен
        pass


@app.post("/api/job/<jid>/project")
def set_project(jid):
    """Проекты записи вручную (ИИ при пересведении их уже не меняет); задачи раскладываются по ним."""
    d = job_or_404(jid)
    b = body()
    names = b["projects"] if isinstance(b.get("projects"), list) else [b.get("project", "")]
    names = list(dict.fromkeys(str(n).strip() for n in names if str(n).strip()))
    for n in names:
        add_project(n)
    set_job_projects(d, names, manual=True)
    return {"ok": True}


@app.post("/api/job/<jid>/task-project")
def set_task_project(jid):
    """Перенести одну задачу в другой проект этой же записи."""
    d = job_or_404(jid)
    res = result_of(d)
    b = body()
    i, name = int(b.get("i", -1)), str(b.get("project", "")).strip()
    tasks = (res or {}).get("tasks") or []
    if not 0 <= i < len(tasks) or not isinstance(tasks[i], dict) or name not in projects_of(res):
        bottle.abort(400, "Нет такой задачи или проекта")
    tasks[i]["project"] = name
    save_result(d, res, relearn=False, what=f"задача → проект «{name}»")
    return {"ok": True}


def set_job_projects(d: Path, names: list, manual: bool = None) -> None:
    extra = {} if manual is None else {"project_manual": manual}
    update_job(d, projects=names, project=names[0] if names else "", **extra)
    res = result_of(d)
    if res:
        set_projects(res, names)
        render.render(d, res)                     # сохраняет и итог.json
        _cache.pop(d / "черновики" / "итог.json", None)


PALETTE = ["#2f6fed", "#e8890c", "#16a374", "#d6455d", "#8a5cf6", "#d64fa8", "#0f9fb3", "#7c9a12",
           "#a0653a", "#c99a06"]
COLORS = APP.parent / "Цвета.json"


def people_colors() -> dict:
    """Постоянный цвет каждого человека: новый получает свободный цвет из палитры (Цвета.json)."""
    import voices
    colors = read_json(COLORS, {}) or {}
    names = [load_settings()["user_name"], *sorted(voices.load_db())]
    for d, j in list_jobs():
        res = cached_json(d / "черновики" / "итог.json", {}) if j.get("status") == "done" else {}
        names += [t["who"] for t in (res or {}).get("turns", [])]
    changed = False
    for n in names:
        if not n or n in colors or n.startswith("Спикер") or n == "?":
            continue
        used = list(colors.values())
        free = [c for c in PALETTE if c not in used]
        colors[n] = free[0] if free else min(PALETTE, key=used.count)
        changed = True
    if changed:
        write_json(COLORS, colors, indent=1)
    return colors


def move_color(old: str, new: str) -> None:
    """При переименовании человека его цвет переходит к новому имени (если у того цвета ещё нет)."""
    colors = read_json(COLORS, {}) or {}
    if old in colors and new not in colors:
        colors[new] = colors.pop(old)
        write_json(COLORS, colors, indent=1)


@app.get("/api/colors")
def colors_get():
    return people_colors()


@app.get("/api/projects")
def projects_list():
    count = {}
    for d, j in list_jobs():
        for p in projects_of(j) or [""]:
            count[p] = count.get(p, 0) + 1
    return {"projects": [{**p, "count": count.get(p["name"], 0)} for p in load_projects()],
            "none": count.get("", 0)}


@app.post("/api/projects")
def projects_save():
    """Список проектов из настроек: переименование (old → name) переносится на записи, удалённые — снимаются."""
    items = [x for x in body().get("items", []) if str(x.get("name", "")).strip()]
    renames = {x["old"]: x["name"].strip() for x in items if x.get("old") and x["old"] != x["name"].strip()}
    keep = {x["name"].strip() for x in items}
    for d, j in list_jobs():
        old = projects_of(j)
        new = [n for n in (renames.get(p, p if p in keep else "") for p in old) if n]
        if new != old:
            res = result_of(d)
            if res:                                   # задачи переходят к новому имени проекта
                for t in res.get("tasks") or []:
                    if isinstance(t, dict) and t.get("project") in renames:
                        t["project"] = renames[t["project"]]
                write_json(d / "черновики" / "итог.json", res)
            set_job_projects(d, list(dict.fromkeys(new)))
    save_projects([{"name": x["name"].strip(), "about": str(x.get("about", "")).strip()} for x in items])
    return projects_list()


@app.post("/api/job/<jid>/undo")
def undo(jid):
    d = job_or_404(jid)
    vs = sorted(versions_dir(d).glob("*.json"))
    if not vs:
        bottle.abort(400, "Отменять нечего")
    res = read_json(vs[-1])
    vs[-1].unlink()
    render.render(d, res)
    _cache.pop(d / "черновики" / "итог.json", None)
    threading.Thread(target=relearn_job, args=(d,), daemon=True).start()
    return {"ok": True, "left": len(vs) - 1}


@app.post("/api/job/<jid>/speakers")
def recount_speakers(jid):
    """Пользователь знает, сколько человек говорило: заново разметка голосов, узнавание, редактура."""
    d = job_or_404(jid)
    j = read_job(d)
    n = int(body().get("n") or 0)
    if j.get("status") == "working" and worker_pid():
        bottle.abort(409, "Запись сейчас обрабатывается — попробуйте, когда закончится")
    backup(d, f"пересчёт голосов: участников {n or 'не задано'}")
    shutil.rmtree(d / "черновики" / "правка", ignore_errors=True)
    # исходная разметка сохранена — пересчитываем только склейку голосов (минуты, а не десятки минут)
    redo = ("voices", "edit", "render") if (d / "черновики" / "голоса-сырые.json").exists() \
        else ("diar", "voices", "edit", "render")
    j["done"] = [k for k in j.get("done", []) if k not in redo]
    j.update(status="queued", error="", attempts={}, num_speakers=n if n > 0 else None,
             editor=load_settings()["editor"])
    write_job(d, j)
    ensure_worker()
    return {"ok": True}


@app.post("/api/job/<jid>/title")
def retitle(jid):
    d = job_or_404(jid)
    res = result_of(d)
    title = body().get("title", "").strip()
    if res and title:
        res["title"] = title
        save_result(d, res, relearn=False, what=f"название «{title}»")
        rename_job_dir(d, title)
    return {"ok": True}


@app.post("/api/job/<jid>/<action:re:retry|redo|rerun|delete|open>")
def job_action(jid, action):
    d = job_or_404(jid)
    j = read_job(d)
    if action == "retry":
        update_job(d, status="queued", error="", attempts={})
    elif action == "redo":
        # заново: узнавание голосов (база могла пополниться), редактура и оформление
        backup(d, "свести итог заново")
        shutil.rmtree(d / "черновики" / "правка", ignore_errors=True)
        j["done"] = [k for k in j.get("done", []) if k not in ("voices", "edit", "render")]
        j.update(status="queued", error="", attempts={}, editor=load_settings()["editor"])
        write_job(d, j)
    elif action == "rerun":
        # всё заново из исходника: распознавание, голоса, редактура (после улучшений программы)
        if j.get("status") == "working" and worker_pid():
            bottle.abort(409, "Запись сейчас обрабатывается — попробуйте, когда закончится")
        backup(d, "распознать заново")
        shutil.rmtree(d / "черновики" / "правка", ignore_errors=True)
        j.update(done=[], status="queued", error="", attempts={}, editor=load_settings()["editor"])
        write_job(d, j)
    elif action == "delete":
        if j.get("status") == "working" and worker_pid():
            bottle.abort(409, "Запись сейчас обрабатывается — удалить можно после")
        shutil.rmtree(d, ignore_errors=True)
        import voices
        db = voices.load_db()
        for e in db.values():
            for key in [k for k in e["jobs"] if k == jid or k.startswith(jid + "#")]:
                e["jobs"].pop(key)
        voices.save_db({k: v for k, v in db.items() if v["jobs"]})
    elif action == "open":
        what = body().get("what", "folder")
        target = d / "видео.mp4" if what == "video" else render.outputs(d).get(what, d)
        open_path(target)
    ensure_worker()
    return {"ok": True}


@app.post("/api/job/<jid>/ask")
def ask_job(jid):
    """Чат с записью: ответ на вопрос или правка расшифровки по словам пользователя."""
    import voices
    d = job_or_404(jid)
    res = result_of(d)
    q = body().get("q", "").strip()
    if not res or not q:
        bottle.abort(400, "Нет вопроса или расшифровки")
    qa_path = d / "черновики" / "вопросы.json"
    qa = read_json(qa_path, [])
    s = load_settings()
    try:
        out = editor.chat(q, res, s, history=qa, people=sorted(voices.load_db()))
        turns, n, who_changed = editor.apply_changes(res["turns"], out["changes"])
        if n:
            res["turns"] = turns
            if who_changed:
                editor.resummarize(res, s)
            save_result(d, res, what=f"чат: {q[:80]}")
    except editor.EditorError as e:
        bottle.abort(502, str(e))
    item = {"q": q, "a": out["reply"], "at": time.time(), "changed": n}
    qa.append(item)
    write_json(qa_path, qa)
    return item


@app.post("/api/job/<jid>/doc")
def make_doc(jid):
    d = job_or_404(jid)
    res = result_of(d)
    kind = body().get("kind")
    if not res or kind not in editor.DOC_SYSTEM:
        bottle.abort(400, "Нет расшифровки")
    path = d / "черновики" / f"документ-{kind}.txt"
    if path.exists() and not body().get("fresh"):
        return {"text": path.read_text(encoding="utf-8")}
    try:
        text = editor.make_doc(kind, res, load_settings())
    except editor.EditorError as e:
        bottle.abort(502, str(e))
    path.write_text(text, encoding="utf-8")
    return {"text": text}


@app.post("/api/job/<jid>/doc-word")
def doc_word(jid):
    from docx import Document
    d = job_or_404(jid)
    kind, text = body().get("kind"), body().get("text", "")
    name = {"letter": "Письмо участникам", "protocol": "Протокол встречи"}.get(kind, "Документ")
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    path = d / f"{render.file_base(result_of(d) or {}, name, limit=50)}.docx"
    doc.save(str(path))
    open_path(path)
    return {"ok": True}


# ---------- поиск и вопросы по всем записям ----------

@app.get("/api/search")
def search():
    q = request.query.getunicode("q", "").strip().lower()
    words = [w for w in re.split(r"\s+", q) if w]
    hits = []
    if not words:
        return {"hits": hits}
    for d, j in list_jobs():
        res = cached_json(d / "черновики" / "итог.json") if j.get("status") == "done" else None
        if not res:
            continue
        for t in res["turns"]:
            low = t["text"].lower()
            if all(w in low for w in words):
                i = low.find(words[0])
                a = max(0, i - 80)
                hits.append({"id": job_id(d), "title": res.get("title", ""), "date": j.get("date", ""),
                             "t": t["t"], "who": t["who"],
                             "snippet": ("…" if a else "") + t["text"][a:a + 240]})
                if len(hits) >= 200:
                    return {"hits": hits}
    return {"hits": hits}


@app.post("/api/ask-all")
def ask_all():
    q = body().get("q", "").strip()
    if not q:
        bottle.abort(400, "Нет вопроса")
    parts = []
    for d, j in sorted(list_jobs(), key=lambda x: x[1].get("ts", 0)):
        res = cached_json(d / "черновики" / "итог.json") if j.get("status") == "done" else None
        if res:
            parts.append(f"ЗАПИСЬ #{job_id(d)}\n{editor.transcript_text(res)}")
    if not parts:
        bottle.abort(400, "Пока нет готовых расшифровок")
    qa_path = JOBS / ".вопросы.json"
    qa = read_json(qa_path, [])
    try:
        a = editor.ask(q, "\n\n".join(parts), load_settings(), many=True, history=qa)
    except editor.EditorError as e:
        bottle.abort(502, str(e))
    qa.append({"q": q, "a": a, "at": time.time()})
    write_json(qa_path, qa[-30:])
    titles = {job_id(d): (cached_json(d / "черновики" / "итог.json") or {}).get("title", j.get("name"))
              for d, j in list_jobs()}
    return {"q": q, "a": a, "titles": titles}


@app.get("/api/ask-all")
def ask_all_history():
    titles = {job_id(d): (cached_json(d / "черновики" / "итог.json") or {}).get("title", j.get("name"))
              for d, j in list_jobs()}
    return {"qa": read_json(JOBS / ".вопросы.json", [])[-10:], "titles": titles}


@app.post("/api/ask-all/clear")
def ask_all_clear():
    """Очистить историю вопросов по всем записям — Claude тоже начнёт разговор заново."""
    write_json(JOBS / ".вопросы.json", [])
    return {"ok": True}


# ---------- вопрос голосом ----------

@app.get("/api/dictate")
def dictate_status():
    return dictation.status()


@app.post("/api/dictate/<action:re:start|stop>")
def dictate_action(action):
    from components import speech_ready
    try:
        if action == "start":
            if not speech_ready():
                bottle.abort(409, "Для вопроса голосом нужна модель GigaAM — установите её в «Настройках»")
            dictation.start(load_settings().get("mic_device", ""))
            return dictation.status()
        return {"text": dictation.stop()}
    except bottle.HTTPError:
        raise
    except Exception as e:  # noqa: BLE001 — ошибку микрофона показываем в окне
        bottle.abort(500, str(e))


# ---------- задачи ----------

@app.get("/api/tasks")
def tasks():
    done_map = read_json(TASKS_STATE, {})
    out = []
    for d, j in list_jobs():
        res = cached_json(d / "черновики" / "итог.json") if j.get("status") == "done" else None
        for t in (res or {}).get("tasks") or []:
            t = t if isinstance(t, dict) else {"what": str(t)}
            jid = job_id(d)
            key = task_key(jid, t.get("what", ""))
            out.append({"key": key, "job": jid, "title": res.get("title", ""), "date": j.get("date", ""),
                        "ts": j.get("ts") or j.get("added") or 0, "who": t.get("who", ""), "what": t.get("what", ""),
                        "when": t.get("when", ""), "done": bool(done_map.get(key)), "t": _sec(t.get("t")),
                        "project": t.get("project") or next(iter(projects_of(j)), "")})
    return {"tasks": out, "user": load_settings()["user_name"]}


def _sec(t):
    """«05:23» → секунды; у старых задач места в разговоре нет."""
    try:
        return parse_time(t) if t not in (None, "") else None
    except ValueError:
        return None


@app.post("/api/tasks/<key>")
def task_done(key):
    done_map = read_json(TASKS_STATE, {})
    done_map[key] = bool(body().get("done"))
    write_json(TASKS_STATE, done_map)
    return {"ok": True}


# ---------- обзор: речь, хронология проекта, итог недели ----------

def _insight(fn, *args):
    try:
        return fn(*args)
    except editor.EditorError as e:
        bottle.abort(502, str(e))


@app.get("/api/insights/speech")
def insights_speech():
    import insights
    return insights.speech(load_settings()["user_name"])


@app.get("/api/insights/lists")
def insights_lists():
    import insights
    return {"projects": insights.project_names(), "weeks": insights.weeks()}


@app.post("/api/insights/timeline")
def insights_timeline():
    import insights
    b = body()
    return _insight(insights.timeline, str(b.get("project", "")), load_settings(), bool(b.get("fresh")),
                    bool(b.get("peek")))


@app.post("/api/insights/week")
def insights_week():
    import insights
    b = body()
    return _insight(insights.week_digest, str(b.get("start", "")), load_settings(), bool(b.get("fresh")),
                    bool(b.get("peek")))


@app.post("/api/insights/week-word")
def insights_week_word():
    import insights
    b = body()
    open_path(insights.week_word(str(b.get("start", "")), b.get("text", "")))
    return {"ok": True}


# ---------- голоса ----------

@app.get("/api/voices")
def voices_list():
    import voices
    db = voices.load_db()
    out = []
    for n, e in sorted(db.items()):
        if not e["jobs"]:
            continue
        samples = []
        for key, x in e["jobs"].items():
            jid = key.split("#")[0]
            clip = x.get("clip") or sample_clip(jid, n)
            samples.append({"key": key, "id": jid, "title": x.get("title", ""), "sec": x["sec"],
                            "clip": clip, "manual": bool(x.get("manual"))})
        out.append({"name": n, "jobs": samples, "sec": round(sum(x["sec"] for x in e["jobs"].values()))})
    todo = sum(1 for d, j in list_jobs() if j.get("status") == "done"
               and not (d / "черновики" / "голоса-отпечатки.json").exists())
    return {"voices": out, "learning": learning, "untrained": todo}


@app.post("/api/voices/rename")
def voices_rename():
    import voices
    old, new = body().get("from", ""), body().get("to", "").strip()
    db = voices.load_db()
    if old in db and new:
        move_color(old, new)
        e = db.pop(old)
        if new in db:
            db[new]["jobs"].update(e["jobs"])
        else:
            db[new] = e
        voices.save_db(db)
        import skype
        for uri, name in read_json(skype.MAP, {}).items():
            if name == old:
                skype.remember(uri, new)
    return {"ok": True}


@app.post("/api/voices/delete")
def voices_delete():
    import voices
    db = voices.load_db()
    db.pop(body().get("name", ""), None)
    voices.save_db(db)
    return {"ok": True}


def clip_audio(jid: str, start: float, dur: float):
    import asr
    return asr.decode_range(find_job(jid) / "запись.mp3", start, dur)


@app.post("/api/voices/move")
def voices_move():
    """Послушали образец — это голос другого человека: переносим образец к нему."""
    import voices
    b = body()
    name, key, to = b.get("name", ""), b.get("key", ""), str(b.get("to", "")).strip()
    db = voices.load_db()
    x = (db.get(name) or {}).get("jobs", {}).get(key)
    if x is not None and not x.get("clip"):
        x["clip"] = sample_clip(key.split("#")[0], name)
        voices.save_db(db)
    if not to or not voices.move(name, key, to, clip_audio):
        bottle.abort(400, "Не получилось перенести образец")
    return {"ok": True}


@app.post("/api/voices/forget")
def voices_forget():
    """Убрать один образец голоса (послушали — голос чужой)."""
    import voices
    voices.forget(body().get("name", ""), body().get("key", ""))
    return {"ok": True}


def sample_clip(jid: str, name: str) -> list:
    """Для старых образцов без отметки времени: самый длинный кусок этого человека в той записи."""
    import voices
    d = find_job(jid)
    if not d:
        return []
    dia = read_json(d / "черновики" / "голоса.json", [])
    res = result_of(d) or {}
    m = voices.full_mapping(dia, res.get("turns", []), read_json(d / "черновики" / "голоса-узнаны.json", {}))
    spk = next((k for k, v in m.items() if v == name), None)
    return voices.longest_clip(dia, spk) if spk is not None else []


@app.post("/api/voices/learn-all")
def voices_learn_all():
    if learning["running"]:
        return {"ok": True}
    threading.Thread(target=_learn_all, daemon=True).start()
    return {"ok": True}


def _learn_all():
    import asr
    import voices
    todo = [d for d, j in list_jobs() if j.get("status") == "done"
            and not (d / "черновики" / "голоса-отпечатки.json").exists()]
    learning.update(running=True, done=0, total=len(todo), message="")
    try:
        for d in todo:
            res = result_of(d) or {}
            dia = read_json(d / "черновики" / "голоса.json", [])
            if res.get("turns") and dia and (d / "запись.mp3").exists():
                clusters = voices.cluster_embeddings(asr.decode(d / "запись.mp3"), dia)
                write_json(d / "черновики" / "голоса-отпечатки.json", clusters)
                relearn_job(d)
            learning["done"] += 1
    except Exception as e:  # noqa: BLE001
        learning["message"] = str(e)
    finally:
        learning["running"] = False


# ---------- словарь и настройки ----------

@app.get("/api/glossary")
def glossary_get():
    return {"text": read_glossary()}


@app.post("/api/glossary")
def glossary_set():
    text = body().get("text")
    if isinstance(text, str):
        GLOSSARY.write_text(text.replace("\r\n", "\n"), encoding="utf-8")
    return {"ok": True}


@app.get("/api/glossary/suggest")
def glossary_suggest():
    import insights
    return insights.suggestions()


@app.post("/api/glossary/suggest")
def glossary_find():
    import insights
    return _insight(insights.find_terms, load_settings())


@app.post("/api/glossary/suggest/dismiss")
def glossary_dismiss():
    import insights
    return insights.dismiss_term(str(body().get("term", "")))


@app.get("/api/settings")
def settings_get():
    try:
        devs = devices()
    except Exception as e:  # noqa: BLE001
        devs = {"mics": [], "default_mic": "", "error": str(e)}
    s = load_settings()
    return {"settings": s, "devices": devs, "codex": codex_status(s), "services": SERVICES,
            "skype_probe": IS_WIN,                 # подсказки Skype для бизнеса есть только в Windows
            "screen": {"supported": screen_supported(), "monitors": screen_monitors()},
            "paths": {"jobs": str(JOBS), "root": str(APP.parent)}}


@app.post("/api/codex-login")
def codex_login():
    """Окно входа в ChatGPT: Codex сам открывает браузер, пароль вводится только там."""
    exe = find_codex(load_settings())
    if not exe:
        bottle.abort(400, "Codex не установлен")
    open_console([exe, "login"], "Вход в ChatGPT")
    return {"ok": True}


@app.get("/api/claude-link")
def claude_link_get():
    import claude_link
    return claude_link.status(load_settings())


@app.post("/api/claude-link")
def claude_link_set():
    """Подключить Qamyal как MCP-сервер ({"on": false} — отключить) в Claude Desktop, Claude Code, Codex
    или только в некоторых: {"which": ["code"]}."""
    import claude_link
    which = [w for w in body().get("which") or claude_link.CLIENTS if w in claude_link.CLIENTS]
    return claude_link.connect(load_settings(), on=body().get("on", True) is not False, which=which)


@app.post("/api/settings")
def settings_set():
    s = load_settings()
    allowed = {"editor", "claude_model", "codex_model", "openai_url", "openai_model", "whisper", "user_name",
               "notify", "theme", "lang", "rec_source", "rec_live", "rec_service", "mic_device", "mini_top",
               "rec_screen", "rec_screen_quality", "rec_screen_monitor"}
    s.update({k: v for k, v in body().items() if k in allowed})
    save_settings(s)
    return {"settings": s}


_mini_lock = threading.Lock()


@app.get("/api/mini")
def mini_get():
    return {"top": bool(load_settings().get("mini_top"))}


@app.post("/api/mini")
def mini_set():
    """Мини-окно. open — открыть (или показать), top — поверх всех окон или нет, main — показать основное окно.
    В Windows окнами управляет программа; на Mac — оболочка Qamyal.app (страница пишет ей сама)."""
    b = body()
    with _mini_lock:                             # место окна и «поверх всех» приходят одновременно — не затираем
        s = load_settings()
        if "top" in b:
            s["mini_top"] = bool(b["top"])
        rect = b.get("rect")                     # где мини-окно (Windows: Chrome сам не помнит)
        if isinstance(rect, list) and len(rect) == 4 and rect[2] <= 900 and rect[3] <= 700:   # не обычная вкладка
            s["mini_rect"] = [int(v) for v in rect]
        if "top" in b or "rect" in b:
            save_settings(s)
    if IS_WIN:
        import sysdeps
        base = f"http://127.0.0.1:{request.urlparts.port}"
        try:
            if b.get("action") == "open":
                sysdeps.open_mini_window(base + "/mini", UI_PROFILE, s["mini_top"], s.get("mini_rect"))
            elif b.get("action") == "main":
                sysdeps.show_main_window(base + "/", UI_PROFILE)
            elif "top" in b:
                sysdeps.set_mini_top(s["mini_top"])
            if isinstance(b.get("size"), list):
                sysdeps.fix_mini_size(*(int(v) for v in b["size"][:2]))
        except RuntimeError as e:
            bottle.abort(409, str(e))
    return {"top": s["mini_top"]}


@app.post("/api/open-folder")
def open_folder():
    open_path(JOBS)
    return {"ok": True}


# ---------- диктофон ----------

@app.get("/api/rec")
def rec_status():
    return rec.status(int(request.query.get("from", 0) or 0))


@app.post("/api/rec/<action:re:start|pause|resume|mark|note|stop|screen>")
def rec_action(action):
    b = body()
    try:
        if action == "start":
            from components import speech_ready
            s = load_settings()
            live = bool(b.get("live", s["rec_live"])) and speech_ready()     # живой расшифровке нужна модель
            shot = bool(b.get("screen", s["rec_screen"])) and screen_supported()
            quality = b.get("screen_quality", s["rec_screen_quality"])
            rec.start(b.get("source", s["rec_source"]), b.get("name", ""), live,
                      s.get("mic_device", ""), int(b.get("speakers") or 0), b.get("service", s["rec_service"]),
                      screen=quality if shot else "", monitor=int(b.get("monitor", s["rec_screen_monitor"]) or 0))
        elif action == "pause":
            rec.pause()
        elif action == "resume":
            rec.resume()
        elif action == "screen":
            s = load_settings()
            if not screen_supported():
                raise RuntimeError("Запись экрана здесь пока недоступна")
            rec.set_screen(bool(b.get("on")), b.get("quality") or s["rec_screen_quality"],
                           int(b.get("monitor", s["rec_screen_monitor"]) or 0))
        elif action == "mark":
            rec.mark(b.get("note", ""))
        elif action == "note":
            rec.note(int(b.get("i", -1)), b.get("text", ""))
        elif action == "stop":
            job = rec.stop(discard=bool(b.get("discard")))
            return {"job": job_id(job) if job else None}
    except Exception as e:  # noqa: BLE001 — ошибку устройства показываем в окне
        bottle.abort(500, str(e))
    return rec.status()


@app.post("/api/rec/hint")
def rec_hint():
    """«Кто говорит» от расширения Chrome (Телемост, Zoom, Teams… в браузере) и разведчика окон программ."""
    events = body().get("events")
    taken = rec.hint(events) if isinstance(events, list) else False
    return {"recording": rec.state in ("recording", "paused"), "taken": taken}


@app.get("/api/rec/hint")
def rec_hint_state():
    """Расширению: идёт ли сейчас запись созвона (тогда стоит присылать подсказки)."""
    import components
    components.extension_seen()
    return {"recording": rec.state in ("recording", "paused") and rec.service not in ("", "skype")}


@app.error(400)
@app.error(404)
@app.error(409)
@app.error(500)
@app.error(502)
def error_json(err):
    response.content_type = "application/json"
    import json
    return json.dumps({"error": err.body or str(err)}, ensure_ascii=False)


def serve(port: int):
    from socketserver import ThreadingMixIn
    from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

    class Server(ThreadingMixIn, WSGIServer):
        daemon_threads = True

    class Quiet(WSGIRequestHandler):
        def log_message(self, *a):
            pass

    return make_server("127.0.0.1", port, app, server_class=Server, handler_class=Quiet)
