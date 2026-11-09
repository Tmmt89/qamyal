"""Общие пути, настройки и работа с заданиями (папками записей)."""
import hashlib
import json
import os
import re
import time
from pathlib import Path

from sysdeps import IS_WIN, default_threads, find_program, gui_python, pid_alive, records_dir, spawn_detached  # noqa: F401

ROOT =Path(__file__).resolve().parent.parent          # D:\Расшифровка
APP = ROOT / "app"
MODELS = ROOT / "models"
JOBS = records_dir(ROOT)


def _move_old_records() -> None:
    """Записи из прежнего места (~/Qamyal/Записи на Mac) — в новое; то, что уже есть на новом месте, не трогаем."""
    old = ROOT / "Записи"
    if old == JOBS or not old.is_dir():
        return
    JOBS.mkdir(parents=True, exist_ok=True)
    for p in old.iterdir():
        if not (JOBS / p.name).exists():
            os.replace(p, JOBS / p.name)
    try:
        old.rmdir()                                    # пустую — убираем, иначе пусть лежит
    except OSError:
        pass


_move_old_records()
GLOSSARY = ROOT / "Словарь.txt"
SETTINGS = APP / "settings.json"
LOCK = JOBS / ".worker.lock"
LOG = JOBS / ".worker.log"
PAUSE = JOBS / ".pause"            # пока файл есть, обработчик стоит на паузе (идёт живая расшифровка)
SERVER = JOBS / ".server.json"     # адрес работающего окна программы
TASKS_STATE = JOBS / ".tasks.json"
INCOMING = JOBS / ".incoming"

os.environ.setdefault("HF_HOME", str(MODELS / "hf"))
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # модели уже скачаны — в интернет не ходим

DEFAULT_SETTINGS = {
    # Кто сводит черновики в итог: "claude" — Claude Code по подписке,
    # "codex" — ChatGPT по подписке через Codex CLI от OpenAI,
    # "openai" — локальная модель через Ollama / LM Studio, "none" — без редактора
    # (итог = текст GigaAM с заменами из словаря, ничего не уходит с компьютера).
    "editor": "claude",
    "claude_exe": "",                        # пусто = искать сам (~/.local/bin, PATH, Homebrew)
    "claude_model": "",                      # пусто = модель по умолчанию в подписке
    "codex_exe": "",                         # пусто = искать сам (tools\codex, PATH, npm)
    "codex_model": "",                       # пусто = модель по умолчанию в подписке ChatGPT
    "openai_url": "http://localhost:11434/v1",
    "openai_model": "qwen3:14b",
    "whisper": True,                         # второй черновик (английские слова, имена)
    "whisper_model": "large-v3-turbo",       # вариант Whisper (components.WHISPER_MODELS)
    "whisper_beam": 5,
    "diar_threshold": 0.5,                   # больше — меньше «спикеров»
    "chunk_minutes": 8,                      # размер куска для редактора
    "threads": default_threads(),            # физические ядра процессора
    "user_name": "Дэни",                     # для «Мои задачи» и подсказки редактору
    "notify": True,                          # уведомление системы, когда расшифровка готова
    "theme": "system",                       # оформление окна: system | light | dark
    "lang": "ru",                            # язык интерфейса: ru | en | ce (нохчийн)
    "rec_source": "mic",                     # mic | system | both
    "rec_live": True,                        # живая расшифровка во время записи
    "rec_service": "skype",                  # через что созвон (см. SERVICES)
    "rec_screen": False,                     # писать экран вместе со звуком
    "rec_screen_quality": "normal",          # low | normal | high (screen.QUALITY)
    "rec_screen_monitor": 0,                 # какой монитор, 0 — основной
    "mic_device": "",                        # пусто = микрофон по умолчанию
    "mini_top": False,                       # мини-окно поверх всех окон
    "mini_rect": None,                       # где и какого размера его оставили (Windows): x, y, ширина, высота
}

# Через что идёт созвон. Кто говорит, сообщает только Skype для бизнеса (официальный SDK);
# для остальных сервис — пометка для записи и подсказка редактору.
SERVICES = {"skype": "Skype для бизнеса", "telemost": "Яндекс Телемост", "mts": "МТС Линк", "zoom": "Zoom",
            "teams": "Microsoft Teams", "networking": "Нетворкинг (Битрикс24)", "messenger": "Telegram / WhatsApp",
            "other": "другой сервис"}

AUDIO_EXT = {".mp3", ".m4a", ".wav", ".ogg", ".opus", ".oga", ".wma", ".aac", ".flac",
             ".amr", ".3gp", ".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi", ".dss", ".mpeg"}

# Этапы обработки: ключ, подпись, доля от длины записи (для оценки оставшегося времени).
STAGES = [
    ("prepare", "подготовка", 0.01),
    ("video", "видео с экрана", 0.01),
    ("gigaam", "распознавание GigaAM", 0.25),
    ("diar", "разметка голосов", 0.35),
    ("voices", "узнавание голосов", 0.03),
    ("whisper", "распознавание Whisper", 1.30),
    ("edit", "редактура", 0.15),
    ("render", "оформление", 0.01),
]
STAGE_LABEL = {k: label for k, label, _ in STAGES}


def load_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    if SETTINGS.exists():
        try:
            s.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    else:
        save_settings(s)
    return s


def find_claude(s: dict) -> str:
    """Где лежит Claude Code; пустая строка — не установлен."""
    exe = s.get("claude_exe")
    return exe if exe and Path(exe).exists() else find_program("claude")


def find_codex(s: dict) -> str:
    """Где лежит Codex CLI (ChatGPT по подписке); пустая строка — не установлен."""
    exe = s.get("codex_exe")
    if exe and Path(exe).exists():
        return exe
    return find_program("codex", [ROOT / "tools" / "codex" / ("codex.exe" if IS_WIN else "codex")])


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def codex_status(s: dict) -> dict:
    exe = find_codex(s)
    return {"installed": bool(exe), "logged_in": bool(exe) and (codex_home() / "auth.json").exists()}


def save_settings(s: dict) -> None:
    SETTINGS.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def fmt_time(sec: float) -> str:
    sec = int(round(sec))
    h, m, s = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_time(t) -> float:
    if isinstance(t, (int, float)):
        return float(t)
    sec = 0.0
    for p in str(t).strip().split(":"):
        sec = sec * 60 + float(p)
    return sec


def fmt_duration(sec: float) -> str:
    m = int(round(sec / 60))
    return f"{m // 60} ч {m % 60:02d} мин" if m >= 60 else f"{m} мин"


def read_json(path: Path, default=None):
    """В Windows файл нельзя прочитать, пока другой процесс подменяет его, — тогда пробуем ещё раз."""
    for attempt in range(20):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return default
        except PermissionError:
            time.sleep(0.05)
        except (OSError, ValueError):
            return default
    return default


def write_json(path: Path, data, indent=None) -> None:
    """Через временный файл (у каждого процесса свой) и подмену: файл не бывает записан наполовину."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:             # файл как раз читают — подождём
            time.sleep(0.05)
    os.replace(tmp, path)


# ---------- задания ----------

def job_id(d: Path, job: dict = None) -> str:
    """Постоянный номер записи (хранится в job.json; папку можно переименовывать)."""
    job = read_job(d) if job is None else job
    return job.get("id") or hashlib.md5(d.name.encode("utf-8")).hexdigest()[:10]


def rename_job_dir(d: Path, title: str) -> Path:
    """Папка записи → «ГГГГ-ММ-ДД Краткое название». Если папка занята (открыта в проводнике,
    файл открыт в Word) — остаётся как была, переименуется при следующем оформлении."""
    job = read_job(d)
    if not job.get("id"):
        job["id"] = job_id(d, job)
        write_job(d, job)
    date = d.name[:10] if re.match(r"\d{4}-\d{2}-\d{2}", d.name) else ""
    short = safe_name(title)
    if len(short) > 70:
        short = short[:70].rsplit(" ", 1)[0].rstrip(" ,.—-")
    base = f"{date} {short}".strip()
    if d.name == base or d.name.startswith(base + " ("):
        return d
    new, n = JOBS / base, 2
    while new.exists():
        new, n = JOBS / f"{base} ({n})", n + 1
    try:
        os.rename(d, new)
        return new
    except OSError:
        return d


def find_job(jid: str):
    for d, j in list_jobs():
        if job_id(d, j) == jid:
            return d
    return None


def read_job(d: Path) -> dict:
    return read_json(d / "job.json", {})


def write_job(d: Path, job: dict) -> None:
    write_json(d / "job.json", job, indent=1)


def update_job(d: Path, **kw) -> dict:
    job = read_job(d)
    if not job and (d / "job.json").exists():
        # не прочиталось (занят, повреждён) — не записываем вместо него обрубок из одних новых полей
        raise RuntimeError(f"не читается {d / 'job.json'}")
    job.update(kw)
    write_job(d, job)
    return job


def list_jobs() -> list:
    """Папки заданий, новые сверху."""
    if not JOBS.exists():
        return []
    items = [(d, read_job(d)) for d in JOBS.iterdir()
             if d.is_dir() and not d.name.startswith(".") and (d / "job.json").exists()]
    items.sort(key=lambda x: x[1].get("added", 0), reverse=True)
    return items


def pending_jobs() -> list:
    """Задания, которые надо обработать, в порядке добавления."""
    jobs = [(d, j) for d, j in list_jobs() if j.get("status") in ("queued", "working")]
    jobs.sort(key=lambda x: x[1].get("added", 0))
    return jobs


def create_job(f: Path, s: dict, move: bool = False, name: str = None, when: float = None,
               extra: dict = None, before=None) -> Path:
    """Новая папка задания с исходником; обработчик подхватит её сам.
    before(папка) — что положить в задание до того, как оно станет видно очереди (job.json пишется последним)."""
    import shutil
    from datetime import datetime

    mt = datetime.fromtimestamp(when or f.stat().st_mtime)
    title = safe_name(name or f.stem)
    base = f"{mt:%Y-%m-%d} {title}"
    d, n = JOBS / base, 2
    while d.exists():
        d, n = JOBS / f"{base} ({n})", n + 1
    (d / "черновики").mkdir(parents=True)
    size = f.stat().st_size
    dst = d / "черновики" / ("исходник" + f.suffix.lower())
    (shutil.move if move else shutil.copy2)(str(f), str(dst))
    job = {"id": hashlib.md5(f"{d.name}|{time.time_ns()}".encode("utf-8")).hexdigest()[:10],
           "name": title, "source": str(f) if not move else f.name, "size": size,
           "date": f"{mt:%d.%m.%Y %H:%M}", "ts": mt.timestamp(), "added": time.time(),
           "status": "queued", "done": [], "whisper": s["whisper"], "editor": s["editor"]}
    job.update(extra or {})
    try:
        if before:
            before(d)
    finally:                 # исходник уже в папке — без job.json очередь его не увидит и запись пропадёт
        write_job(d, job)
    return d


VERSIONS_KEEP = 30


def versions_dir(d: Path) -> Path:
    return d / "черновики" / "версии"


def backup(d: Path, what: str) -> None:
    """Прежний итог — в черновики\\версии; его возвращает «Отменить»."""
    import shutil
    cur = d / "черновики" / "итог.json"
    if not cur.exists():
        return
    vd = versions_dir(d)
    vd.mkdir(exist_ok=True)
    shutil.copy2(cur, vd / f"{time.time_ns()}.json")
    with (vd / "журнал.txt").open("a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%d.%m %H:%M')} {what}\n")
    for old in sorted(vd.glob("*.json"))[:-VERSIONS_KEEP]:
        old.unlink()


def safe_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", name).strip(" .")
    return re.sub(r"\s+", " ", name)[:80] or "Запись"


def eta(job: dict) -> float:
    """Сколько примерно осталось секунд до конца задания."""
    dur = job.get("duration") or 0
    if not dur:
        return 0
    stage, prog = job.get("stage"), (job.get("progress") or 0) / 100
    from components import whisper_ready, whisper_speed
    weights = {k: w for k, _, w in STAGES}
    weights["whisper"] = whisper_speed() if job.get("whisper", True) and whisper_ready() else 0
    done = set(job.get("done", []))
    return dur * sum(w * (1 - prog if k == stage else 1) for k, w in weights.items() if k not in done)


# ---------- проекты ----------

PROJECTS = ROOT / "Проекты.json"


def load_projects() -> list:
    """[{"name": "Тренажёр ННБ", "about": "о чём проект — подсказка для ИИ"}]"""
    return read_json(PROJECTS, []) or []


def save_projects(items: list) -> None:
    write_json(PROJECTS, items, indent=1)


def add_project(name: str, about: str = "") -> None:
    """Новый проект — в список; у известного проекта без описания описание появляется."""
    name, about = (name or "").strip(), (about or "").strip()
    items = load_projects()
    same = [p for p in items if p["name"].lower() == name.lower()]
    if name and not same:
        items.append({"name": name, "about": about})
        save_projects(items)
    elif same and about and not same[0].get("about"):
        same[0]["about"] = about
        save_projects(items)


def projects_of(x: dict) -> list:
    """Проекты записи (из job.json или итога): список; старые записи хранили один проект строкой."""
    p = (x or {}).get("projects")
    if isinstance(p, list):
        return [str(n).strip() for n in p if str(n).strip()]
    one = (x or {}).get("project")
    return [one.strip()] if isinstance(one, str) and one.strip() else []


def task_key(jid: str, what: str) -> str:
    """Постоянный ключ задачи — по нему хранится отметка «сделано» (.tasks.json)."""
    return hashlib.md5(f"{jid}|{what}".encode("utf-8")).hexdigest()[:12]


def settle_tasks(res: dict) -> None:
    """Каждая задача — в один из проектов записи (если ИИ не указал или указал чужой — в главный)."""
    ps = projects_of(res)
    for t in res.get("tasks") or []:
        if isinstance(t, dict) and t.get("project") not in ps:
            t["project"] = ps[0] if ps else ""


def set_projects(res: dict, names: list) -> None:
    res["projects"] = list(dict.fromkeys(n for n in names if n))
    res["project"] = res["projects"][0] if res["projects"] else ""     # главный — для старых мест
    settle_tasks(res)


def projects_block() -> str:
    items = load_projects()
    return "\n".join(f"- {p['name']}" + (f": {p['about']}" if p.get("about") else "") for p in items) or "(пока нет)"


# ---------- словарь ----------

def read_glossary() -> str:
    try:
        return GLOSSARY.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def glossary_rules() -> list:
    """Пары (неправильно → правильно) из строк вида «Правильно (пояснение) — вариант, вариант»."""
    rules = []
    for line in read_glossary().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.split(r"\s+[—–-]\s+", line, maxsplit=1)
        if len(m) < 2:
            continue
        right = re.sub(r"\s*\(.*?\)\s*", " ", m[0]).strip()
        for wrong in m[1].split(","):
            wrong = wrong.strip()
            if wrong and wrong.lower() != right.lower() and len(wrong) > 2:
                rules.append((wrong, right))
    return rules


# ---------- процессы ----------

def worker_pid() -> int:
    """PID работающего обработчика или 0."""
    try:
        pid = int(LOCK.read_text())
    except (OSError, ValueError):
        return 0
    return pid if pid_alive(pid) else 0


def spawn_worker() -> None:
    from components import speech_ready
    if speech_ready():                     # без распознавания записи ждут в очереди, пока его не скачают
        spawn_detached([gui_python(), str(APP / "worker.py")], APP)
