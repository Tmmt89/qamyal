"""Редактура: из двух черновиков с разметкой голосов собирается итоговый текст."""
import json
import re
import subprocess
import urllib.request
from pathlib import Path

from common import (APP, find_claude, find_codex, fmt_time, glossary_rules, parse_time, projects_block,
                    read_glossary, settle_tasks)
from sysdeps import HIDDEN

EDIT_SYSTEM = """Ты — редактор расшифровок рабочих разговоров на русском языке. Разговоры в основном про наклонно-направленное бурение (ННБ) и разработку тренажёра-симулятора, но могут быть и о другом.

На вход приходит фрагмент записи в двух автоматических черновиках:
• Черновик А — GigaAM. Точнее распознаёт русскую речь и почти ничего не пропускает, но плохо слышит английские слова, названия и имена.
• Черновик Б — Whisper. Лучше слышит английские слова, названия и имена, но чаще ошибается в русских словах, иногда пропускает куски или выдаёт бессмыслицу.
Реплики в черновиках уже разбиты по голосам («Спикер 1», «Спикер 2»…), но разметка приблизительная: короткие реплики и поддакивания бывают приписаны не тому, один человек иногда раздроблен на несколько «спикеров», в одной реплике бывают слова двух людей.

Собери из черновиков один точный и читаемый текст фрагмента:
1. Основа — черновик А. Из черновика Б бери английские слова, названия, имена и места, где А явно ошибся или пропустил.
2. Кто говорит — решай по смыслу, а не только по меткам. Имена участников определяй по подсказкам «узнаны по голосу» (это надёжно: отступай, только если смысл явно противоречит), по обращениям по имени, по названию записи и по ролям людей из словаря (кто эксперт, кто разработчик и т. п.); если уверенности нет, оставь «Спикер N». Одного человека везде называй одинаково.
3. Термины и имена пиши так, как в словаре.
4. Убирай слова-паразиты, запинки, повторы, бессмысленные поддакивания («угу», «ага», «да-да» на фоне чужой речи) и мат-междометия. Короткий содержательный ответ («Да», «Понял», «Нет») оставляй отдельной репликой.
5. Не пересказывай и не сокращай мысль: сохраняй формулировки и разговорный стиль говорящего, правь только то, что мешает читать.
6. Ничего не выдумывай. Если место не разобрать ни по одному черновику — пиши [неразборчиво]; если слово угадано, но нет уверенности — ставь после него (?).
7. Время реплики — по ближайшей отметке [ММ:СС] в черновике А перед её началом (отметки стоят в начале реплик и внутри длинных реплик). В итоговом тексте отметок времени быть не должно.
8. Длинный монолог разбивай на абзацы по 2–5 предложений, у каждого своё время.

Ответь только JSON, без пояснений и без markdown:
{"speakers": {"Спикер 1": "Имя или Спикер 1"}, "turns": [{"t": "05:23", "who": "Имя", "text": "…"}]}"""

SUMMARY_SYSTEM = """Ты готовишь краткое содержание рабочего разговора по его расшифровке. Пиши по-русски, деловым языком, без воды, только то, что есть в разговоре. Участников называй как в расшифровке.

Определи ещё, к каким проектам относится разговор (поле projects): названия из списка ПРОЕКТЫ — по описаниям и по смыслу. На одном созвоне часто обсуждают несколько проектов: перечисли все, о которых говорили по существу, главный — первым; мимолётные упоминания не в счёт. Если для темы ни один проект из списка не подходит — придумай короткое новое название (2–4 слова, как назвал бы его сам участник). Для новых проектов и для проектов из списка без описания дай описание одной фразой в project_about. Если разговор не о работе — пустой список.
У каждой задачи укажи project — к какому из проектов разговора она относится.

Ответь только JSON, без пояснений и без markdown:
{"title": "короткое название разговора, 3–8 слов", "projects": ["главный проект", "другой проект"], "project_about": {"проект без описания": "одна фраза: о чём он, кто участвует"}, "summary": ["главные темы и выводы, 3–8 пунктов"], "decisions": ["что решили; пустой список, если ничего"], "tasks": [{"who": "кто", "what": "что сделать", "when": "срок или пустая строка", "project": "проект задачи", "t": "ММ:СС — где в разговоре об этом договорились"}]}"""


def summary_prompt(text: str) -> str:
    return (f"ПРОЕКТЫ:\n{projects_block()}\n\nСЛОВАРЬ:\n{read_glossary().strip()}\n\nРАСШИФРОВКА:\n{text}")


SCREENS_MAX = 40          # больше кадров Claude не показываем: дорого и долго


def screens_block(job_dir: Path) -> tuple:
    """Кадры записи экрана для краткого содержания: (текст для запроса, папка с кадрами) или ("", None)."""
    try:
        frames = json.loads((job_dir / "job.json").read_text(encoding="utf-8")).get("frames") or []
    except (OSError, ValueError):
        return "", None
    frames = [f for f in frames if (job_dir / f["file"]).exists()]
    if not frames:
        return "", None
    if len(frames) > SCREENS_MAX:                     # равномерно по всей записи
        step = len(frames) / SCREENS_MAX
        frames = [frames[int(i * step)] for i in range(SCREENS_MAX)]
    listing = "\n".join(f"[{fmt_time(f['t'])}] {job_dir / f['file']}" for f in frames)
    text = ("\n\nЭКРАН: во время разговора записывался экран. Вот кадры в моменты, когда он менялся "
            "(слайды презентации, окна программ), со временем появления:\n"
            f"{listing}\n"
            "Открой их инструментом Read. Учитывай, что было на экране, в кратком содержании, решениях и задачах — "
            "когда это помогает понять разговор (о каком слайде, ошибке или окне шла речь). Отдельно кадры не пересказывай; "
            "если на экране происходило что-то, о чём в разговоре не говорят, в краткое содержание это не пиши. "
            'Добавь в ответ поле "screens": {"имя файла, например 001.jpg": "что на экране, до 12 слов"} — '
            "для каждого кадра из списка.")
    return text, job_dir / frames[0]["file"].split("/")[0]


class EditorError(RuntimeError):
    pass


# ---------- вызов модели ----------

def call_claude(system: str, prompt: str, s: dict, look: Path = None) -> str:
    """look — папка с картинками, которые Claude может открыть сам (инструмент Read, только чтение)."""
    exe = find_claude(s)
    if not exe:
        raise EditorError("Не найден Claude Code — установите его или выберите другой вариант в Настройках")
    cwd = APP / "editor_cwd"
    cwd.mkdir(exist_ok=True)
    cmd = [exe, "-p", "--output-format", "json", "--tools", "Read" if look else "", "--no-session-persistence",
           "--system-prompt", system]
    if look:
        cmd += ["--allowedTools", "Read", "--add-dir", str(look)]
    if s.get("claude_model"):
        cmd += ["--model", s["claude_model"]]
    # обычно часть текста — 1–3 минуты; 09.11 вызов однажды просто повис на 30 минут, а повтор сразу прошёл —
    # поэтому ждём до 15 минут и при зависании пробуем ещё раз
    for attempt in range(2):
        try:
            p = subprocess.run(cmd, input=prompt.encode("utf-8"), capture_output=True, cwd=cwd,
                               timeout=900, **HIDDEN)
            break
        except subprocess.TimeoutExpired:
            if attempt:
                raise EditorError("Claude дважды не ответил за 15 минут — проверьте интернет и нажмите «Повторить»")
    out = p.stdout.decode("utf-8", "replace").strip()
    try:
        res = json.loads(out)
    except ValueError:
        err = (p.stderr.decode("utf-8", "replace") or out).strip()
        raise EditorError(f"Claude Code: {err[:300] or 'код ' + str(p.returncode)}")
    if res.get("is_error"):
        raise EditorError(f"Claude: {str(res.get('result'))[:300]}")
    return res.get("result") or ""


def call_codex(system: str, prompt: str, s: dict) -> str:
    """ChatGPT по подписке: Codex CLI в режиме «только ответ», без права что-либо менять."""
    import tempfile
    exe = find_codex(s)
    if not exe:
        raise EditorError("Не установлен Codex — программа OpenAI для работы по подписке ChatGPT")
    cwd = APP / "editor_cwd"
    cwd.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        out_file = Path(tmp) / "answer.txt"
        cmd = [exe, "exec", "--skip-git-repo-check", "--sandbox", "read-only", "--color", "never",
               "-C", str(cwd), "-o", str(out_file)]
        if s.get("codex_model"):
            cmd += ["-m", s["codex_model"]]
        task = (f"{system}\n\nНе запускай команды и не открывай файлы: всё нужное — ниже. "
                f"Сразу дай ответ в требуемом виде.\n\n{prompt}")
        try:
            p = subprocess.run(cmd + ["-"], input=task.encode("utf-8"), capture_output=True, cwd=cwd,
                               timeout=1800, **HIDDEN)
        except subprocess.TimeoutExpired:
            raise EditorError("ChatGPT не ответил за 30 минут")
        text = out_file.read_text(encoding="utf-8").strip() if out_file.exists() else ""
    if not text:
        err = (p.stderr.decode("utf-8", "replace") or p.stdout.decode("utf-8", "replace")).strip()
        if "login" in err.lower() or "auth" in err.lower():
            raise EditorError("ChatGPT: нужно войти в аккаунт (Настройки → «Войти в ChatGPT»)")
        raise EditorError(f"ChatGPT (Codex): {err[-300:] or 'код ' + str(p.returncode)}")
    return text


def call_openai(system: str, prompt: str, s: dict) -> str:
    body = json.dumps({
        "model": s["openai_model"], "temperature": 0.2, "stream": False,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(s["openai_url"].rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=4 * 3600) as r:
            res = json.loads(r.read().decode("utf-8"))
    except OSError as e:
        raise EditorError(f"Локальная модель недоступна ({s['openai_url']}): {e}")
    text = res["choices"][0]["message"]["content"]
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S)


def caller(s: dict):
    if s["editor"] == "none":
        raise EditorError("В настройках выбран режим «без редактора» — текст записей никуда не "
                          "отправляется, поэтому чат, вопросы и документы недоступны.")
    return {"openai": call_openai, "codex": call_codex}.get(s["editor"], call_claude)


def ask_json(system: str, prompt: str, s: dict, look: Path = None) -> dict:
    call = caller(s)
    extra = {"look": look} if look and call is call_claude else {}     # картинки умеет смотреть только Claude Code
    last = ""
    for attempt in range(3):
        text = call(system, prompt if attempt == 0 else
                    prompt + "\n\nПредыдущий ответ не разобрался как JSON. Ответь строго одним JSON-объектом.", s, **extra)
        try:
            return parse_json(text)
        except ValueError as e:
            last = f"{e}: {text[:200]}"
    raise EditorError(f"Редактор вернул не JSON ({last})")


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b < a:
        raise ValueError("нет JSON")
    return json.loads(text[a:b + 1])


# ---------- куски для редактора ----------

def lines(turns: list) -> str:
    return "\n".join(f"[{fmt_time(t['s'])}] {t['who']}: {t['text']}" for t in turns)


def split_chunks(turns_a: list, minutes: float) -> list:
    """Границы кусков (сек) — по началу реплик черновика А."""
    if not turns_a:
        return []
    bounds, limit = [0.0], minutes * 60
    for t in turns_a:
        if t["s"] - bounds[-1] >= limit:
            bounds.append(t["s"])
    bounds.append(float("inf"))
    return list(zip(bounds[:-1], bounds[1:]))


def in_range(turns: list, a: float, b: float) -> list:
    return [t for t in turns if a <= t["s"] < b]


def edit(job_dir: Path, job_name: str, a_turns: list, b_turns: list, s: dict, progress,
         hints: str = "") -> dict:
    """Возвращает итог: название, краткое содержание, реплики."""
    work = job_dir / "черновики" / "правка"
    work.mkdir(parents=True, exist_ok=True)
    glossary = read_glossary().strip() or "(пусто)"
    voice_note = f"О ЗАПИСИ И УЧАСТНИКАХ (узнаны по голосу или по Skype):\n{hints}\n\n" if hints else ""
    owner = f"Записи делает {s.get('user_name', 'Дэни')}: почти всегда он один из собеседников.\n\n"
    chunks = split_chunks(a_turns, s["chunk_minutes"])
    speakers, turns = {}, []
    for i, (a, b) in enumerate(chunks, 1):
        part = work / f"часть-{i:02d}.json"
        if part.exists():
            res = json.loads(part.read_text(encoding="utf-8"))
        else:
            known = "\n".join(f"{k} = {v}" for k, v in speakers.items()) or "пока ничего"
            tail = lines([{"s": t["t"], "who": t["who"], "text": t["text"]} for t in turns[-4:]])
            prompt = (f"НАЗВАНИЕ ЗАПИСИ: {job_name}\n\n{owner}{voice_note}"
                      f"СЛОВАРЬ ТЕРМИНОВ И ИМЁН:\n{glossary}\n\n"
                      f"ИЗВЕСТНО ИЗ ПРЕДЫДУЩИХ ЧАСТЕЙ:\nУчастники: {known}\n"
                      + (f"Конец предыдущей части:\n{tail}\n" if tail else "")
                      + f"\nФРАГМЕНТ {i} из {len(chunks)}\n\n"
                      f"ЧЕРНОВИК А (GigaAM):\n{lines(in_range(a_turns, a, b))}\n\n"
                      f"ЧЕРНОВИК Б (Whisper):\n{lines(in_range(b_turns, a, b)) or '(нет)'}")
            res = ask_json(EDIT_SYSTEM, prompt, s)
            part.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        speakers.update(res.get("speakers") or {})
        for t in res.get("turns") or []:
            try:
                sec = parse_time(t.get("t", a))
            except ValueError:
                sec = a
            if t.get("text"):
                turns.append({"t": sec, "who": t.get("who") or "?", "text": t["text"].strip()})
        progress(int(i * 90 / max(1, len(chunks))))

    summ_file = work / "кратко.json"
    if summ_file.exists():
        summary = json.loads(summ_file.read_text(encoding="utf-8"))
    else:
        text = "\n".join(f"[{fmt_time(t['t'])}] {t['who']}: {t['text']}" for t in turns)
        screens, look = screens_block(job_dir) if s.get("editor", "claude") == "claude" else ("", None)
        summary = ask_json(SUMMARY_SYSTEM, summary_prompt(text) + screens, s, look=look)
        summ_file.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    progress(100)
    return {**summary, "turns": turns}


def plain(a_turns: list, matches: dict = None) -> dict:
    """Без редактора: текст GigaAM по голосам с заменами из словаря и именами, узнанными по голосу."""
    rules = [(re.compile(rf"(?<!\w){re.escape(w)}(?!\w)", re.I), r) for w, r in glossary_rules()]
    names = {lab: m["name"] for lab, m in (matches or {}).items()}
    turns = []
    for t in a_turns:
        text = re.sub(r"\s*\[\d+:\d{2}(?::\d{2})?\]", "", t["text"])
        for rx, right in rules:
            text = rx.sub(right, text)
        turns.append({"t": t["s"], "who": names.get(t["who"], t["who"]), "text": text})
    return {"title": "", "summary": [], "decisions": [], "tasks": [], "turns": turns}


# ---------- вопросы к записям и документы ----------

ASK_SYSTEM = """Ты помогаешь разобраться в записях рабочих разговоров. Отвечай по-русски, коротко и по делу, только на основе расшифровок. Если в записях этого нет — так и скажи. Ссылайся на места записей: {cite}. По этим ссылкам можно перейти к месту записи. Без markdown-заголовков и таблиц; простые списки можно, **жирный** — для главного."""

DOC_SYSTEM = {
    "letter": """Напиши письмо участникам разговора от имени {user}. Структура: первая строка «Тема: …»; короткое приветствие; итоги разговора по пунктам; что решили; задачи — кто, что, к какому сроку; просьба поправить, если что-то упущено или понято неверно. Тон деловой и дружелюбный, без канцелярита, на «вы» или на «ты» — как обращались друг к другу в разговоре. Только текст письма, без пояснений и без markdown.""",
    "protocol": """Составь протокол встречи по расшифровке. Разделы: «Дата», «Участники», «Обсуждали» (вопросы по пунктам с кратким содержанием), «Решения», «Задачи» (кто — что — срок; если срок не назван, так и пиши: «срок не назван»). Простой текст со списками, без markdown и таблиц, без вступлений и пояснений.""",
}


def transcript_text(res: dict) -> str:
    head = f"Название: {res.get('title', '')}\nДата: {res.get('date', '')}\n"
    return head + "\n".join(f"[{fmt_time(t['t'])}] {t['who']}: {t['text']}" for t in res.get("turns", []))


def ask_text(system: str, prompt: str, s: dict) -> str:
    return caller(s)(system, prompt, s).strip()


CHAT_SYSTEM = """Ты помогаешь с расшифровкой рабочего разговора: отвечаешь на вопросы о нём и, когда пользователь просит, исправляешь расшифровку.

Расшифровка дана построчно: «#номер [ММ:СС] Кто: текст». Кто говорит, размечено автоматически и может быть неверно: один человек бывает раздроблен на несколько «Спикеров», реплики бывают приписаны не тому, в одной реплике могут оказаться слова двух людей.

Если пользователь спрашивает — ответь коротко и по делу, ссылаясь на места временем в квадратных скобках, например [12:34]; ничего не меняй.
Если пользователь просит исправить (кто говорит, имена, слова, термины, лишние или ошибочные реплики) — внеси правки и в ответе коротко скажи, что сделал. Меняй то, о чём просят, и то, что из этого явно следует. Например, «говорили только я и Рафаэль» — каждую реплику каждого «Спикера N» припиши одному из двоих по смыслу, обращениям и манере речи; если реплика явно состоит из слов обоих — раздели её текст между двумя репликами (вторую часть добавь через "split"). Текст реплик не пересказывай и не сокращай, только исправляй ошибки.

Ответь только JSON, без markdown:
{"reply": "ответ пользователю", "changes": [
  {"i": 3, "who": "Рафаэль"},
  {"i": 5, "text": "исправленный текст"},
  {"i": 7, "delete": true},
  {"i": 9, "split": {"text": "текст, который остаётся в реплике 9", "who2": "Дэни", "text2": "отделённая часть — новая реплика сразу после"}}
]}
Если править нечего — "changes": []."""


def chat(message: str, res: dict, s: dict, history: list = None, people: list = None) -> dict:
    """Сообщение пользователя о записи → {"reply", "changes"} (правки применяет сервер)."""
    lines = "\n".join(f"#{i} [{fmt_time(t['t'])}] {t['who']}: {t['text']}" for i, t in enumerate(res["turns"]))
    prev = "".join(f"\nПОЛЬЗОВАТЕЛЬ: {h['q']}\nТЫ: {h['a']}\n" for h in (history or [])[-4:])
    prompt = (f"Записи делает {s.get('user_name', 'Дэни')}: почти всегда он один из собеседников.\n"
              + (f"ЛЮДИ, ЧЬИ ГОЛОСА ИЗВЕСТНЫ ПРОГРАММЕ: {', '.join(people)}\n" if people else "")
              + f"\nСЛОВАРЬ:\n{read_glossary().strip()}\n\n"
              f"РАСШИФРОВКА «{res.get('title', '')}» ({res.get('date', '')}):\n{lines}\n"
              + (f"\nПРЕДЫДУЩИЕ СООБЩЕНИЯ:{prev}" if prev else "")
              + f"\nСООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ: {message}")
    out = ask_json(CHAT_SYSTEM, prompt, s)
    if not isinstance(out.get("changes"), list):
        out["changes"] = []
    out["reply"] = str(out.get("reply") or "Готово.")
    return out


def apply_changes(turns: list, changes: list) -> tuple:
    """Правки из чата → новый список реплик. Возвращает (реплики, сколько изменено, менялись ли имена)."""
    turns = [dict(t) for t in turns]
    extra, dropped, n, who_changed = {}, set(), 0, False
    for c in changes:
        try:
            i = int(c.get("i"))
        except (TypeError, ValueError):
            continue
        if not 0 <= i < len(turns):
            continue
        t = turns[i]
        if c.get("delete"):
            dropped.add(i)
            n += 1
            continue
        if c.get("who") and str(c["who"]).strip() != t["who"]:
            t["who"] = str(c["who"]).strip()
            who_changed = True
            n += 1
        if c.get("text") and str(c["text"]).strip() != t["text"]:
            t["text"] = str(c["text"]).strip()
            n += 1
        sp = c.get("split")
        if isinstance(sp, dict) and sp.get("text2"):
            if sp.get("text"):
                t["text"] = str(sp["text"]).strip()
            nxt = turns[i + 1]["t"] if i + 1 < len(turns) else t["t"] + 5
            extra.setdefault(i, []).append({"t": round((t["t"] + nxt) / 2, 1),
                                            "who": str(sp.get("who2") or t["who"]).strip(),
                                            "text": str(sp["text2"]).strip()})
            who_changed = True
            n += 1
    out = []
    for i, t in enumerate(turns):
        if i not in dropped:
            out.append(t)
        out.extend(extra.get(i, []))
    return out, n, who_changed


def resummarize(res: dict, s: dict) -> dict:
    """Краткое содержание, решения и задачи заново (после смены имён); название остаётся."""
    text = "\n".join(f"[{fmt_time(t['t'])}] {t['who']}: {t['text']}" for t in res["turns"])
    new = ask_json(SUMMARY_SYSTEM, summary_prompt(text), s)
    for k in ("summary", "decisions", "tasks"):
        if k in new:
            res[k] = new[k]
    settle_tasks(res)                    # проекты записи остаются прежними, задачи раскладываются по ним
    return res


def ask(question: str, context: str, s: dict, many: bool = False, history: list = None) -> str:
    cite = ("пиши [#номер ММ:СС], где номер — из строки «ЗАПИСЬ #номер»" if many
            else "пиши время в квадратных скобках, например [12:34]")
    prev = "".join(f"\nВОПРОС: {h['q']}\nОТВЕТ: {h['a']}\n" for h in (history or [])[-4:])
    prompt = (f"СЛОВАРЬ:\n{read_glossary().strip()}\n\nРАСШИФРОВК{'И' if many else 'А'}:\n{context}\n"
              + (f"\nПРЕДЫДУЩИЕ ВОПРОСЫ:{prev}" if prev else "") + f"\nВОПРОС: {question}")
    return ask_text(ASK_SYSTEM.format(cite=cite), prompt, s)


def make_doc(kind: str, res: dict, s: dict) -> str:
    from datetime import datetime
    system = DOC_SYSTEM[kind].format(user=s.get("user_name", "Дэни")) + \
        f"\nСегодня {datetime.now():%d.%m.%Y}; дата разговора указана в расшифровке."
    extra = ""
    if res.get("summary"):
        extra = "\n\nКРАТКОЕ СОДЕРЖАНИЕ (уже составлено):\n" + "\n".join(f"- {x}" for x in res["summary"])
    return ask_text(system, transcript_text(res) + extra, s)
