"""Созвоны в Skype для бизнеса: кто когда говорил — по журналу разведчика (официальный Lync SDK).

Skype показывает одного «говорящего сейчас» и держит его, пока не заговорит другой, поэтому
сам по себе журнал не знает пауз. Речь находим по звуку (VAD), а журнал говорит, чья она:
левый канал — микрофон (хозяин записи), правый — собеседники, имя — от Skype."""
import json
import re
from pathlib import Path

import numpy as np

from common import ROOT, read_json, write_json

MAP = ROOT / "Голоса" / "skype.json"         # адрес в Skype → имя в Qamyal (запоминается при переименовании)
SR = 16000

# полное имя → как его обычно зовут в разговоре (берётся, только если так человек уже записан в «Голосах»)
SHORT = {"евгений": ["Женя"], "александр": ["Саша"], "дмитрий": ["Дима"], "владимир": ["Вова", "Володя"],
         "михаил": ["Миша"], "сергей": ["Серёжа"], "алексей": ["Лёша"], "николай": ["Коля"],
         "анатолий": ["Толя"], "екатерина": ["Катя"], "елена": ["Лена"], "татьяна": ["Таня"],
         "мария": ["Маша"], "анастасия": ["Настя"], "юлия": ["Юля"], "павел": ["Паша"], "иван": ["Ваня"]}

_PAIRS = [("shch", "щ"), ("sch", "щ"), ("zh", "ж"), ("kh", "х"), ("ts", "ц"), ("ch", "ч"), ("sh", "ш"),
          ("yu", "ю"), ("ya", "я"), ("yo", "ё"), ("ye", "е"), ("ks", "кс"), ("x", "кс"), ("ph", "ф")]
_ONE = dict(zip("abvgdezijklmnoprstufhcywq", "абвгдезийклмнопрстуфхкывк"))


FIXED = {"rafael": "Рафаэль", "alexander": "Александр", "aleksandr": "Александр", "yuri": "Юрий",
         "yury": "Юрий", "michael": "Михаил", "daniel": "Даниил", "emil": "Эмиль", "ilya": "Илья",
         "olga": "Ольга", "natalia": "Наталья", "natalya": "Наталья", "igor": "Игорь"}


def translit(word: str) -> str:
    w = word.lower()
    if w in FIXED:
        return FIXED[w]
    w = re.sub(r"(?<=[^aeiouy])y$", "iy", w)                 # Evgeny → Евгений, Dmitry → Дмитрий
    out, i = "", 0
    while i < len(w):
        for lat, cyr in _PAIRS + [("iy", "ий"), ("ey", "ей"), ("ay", "ай"), ("oy", "ой")]:
            if w.startswith(lat, i):
                out, i = out + cyr, i + len(lat)
                break
        else:
            out, i = out + _ONE.get(w[i], w[i]), i + 1
    return out[:1].upper() + out[1:]


def _norm(name: str) -> str:
    return name.lower().replace("ь", "").replace("э", "е").replace("ё", "е")


def first_name(display: str) -> str:
    """«Bagautdinov, Ural» → «Ural»; «Ural Bagautdinov» → «Ural»."""
    part = display.split(",", 1)[1] if "," in display else display
    words = part.split()
    return words[0] if words else display


def person_name(uri: str, display: str, is_self: bool, user_name: str, known: list) -> str:
    """Имя участника в Qamyal: запомненное → своё → как он записан в «Голосах» → транслит имени."""
    saved = read_json(MAP, {})
    if uri in saved:
        return saved[uri]
    if is_self:
        return user_name
    first = first_name(display)
    if re.search("[а-яА-ЯёЁ]", first):
        cyr = first
    else:
        cyr = translit(first)
    by_norm = {_norm(k): k for k in known}
    for cand in [cyr] + SHORT.get(cyr.lower(), []):
        if _norm(cand) in by_norm:
            return by_norm[_norm(cand)]
    return cyr


def remember(uri: str, name: str) -> None:
    m = read_json(MAP, {})
    m[uri] = name
    MAP.parent.mkdir(exist_ok=True)
    write_json(MAP, m)


# ---------- журнал ----------

def _to_rec(anchors: list):
    """Время на часах → секунда записи (паузы записи выпадают)."""
    anchors = sorted(anchors or [[0.0, 0.0]])

    def conv(t):
        cur = anchors[0]
        for k, a in enumerate(anchors):
            if a[1] <= t:
                cur = a
                nxt = anchors[k + 1] if k + 1 < len(anchors) else None
                if nxt is not None:
                    pause_from = a[1] + (nxt[0] - a[0])     # когда началась пауза
                    if pause_from <= t < nxt[1]:
                        return nxt[0]
        return cur[0] + max(0.0, t - cur[1])

    return conv


def timeline(log: Path, anchors: list, duration: float):
    """Отрезки «говорит Skype-участник» в секундах записи + участники. None — журнал не пригоден."""
    if not log.exists() or not anchors:
        return None
    ev = []
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            ev.append(json.loads(line))
        except ValueError:
            pass
    people, opened, segs, seen = {}, {}, [], set()
    start = ev[0]["t"] if ev else 0
    for e in ev:
        uri = e.get("uri")
        if e["kind"] == "participant" and uri:
            people.setdefault(uri, {"display": e.get("name", ""), "self": bool(e.get("self"))})
        elif e["kind"] == "speak_start" and uri:
            opened[uri] = e["t"]
        elif e["kind"] == "speak_end" and uri:
            s = opened.pop(uri, None)
            if s is None and uri not in seen:
                s = start                                       # говорил уже, когда запись началась
            if s is not None:
                segs.append([s, e["t"], uri])
                seen.add(uri)
    end = ev[-1]["t"] if ev else start
    segs += [[s, end, uri] for uri, s in opened.items()]
    conv = _to_rec(anchors)
    out = []
    for s, e, uri in sorted(segs):
        a, b = conv(s), min(conv(e), duration)
        if b - a > 0.2 and uri in people:
            out.append((round(a, 2), round(b, 2), uri))
    talkers = {u for _, _, u in out}
    covered = sum(b - a for a, b, _ in out)
    if len(talkers) < 2 or covered < 0.3 * duration:
        return one_on_one(ev, people, conv, duration)
    return out, people


def one_on_one(ev: list, people: dict, conv, duration: float):
    """Звонок один на один. Skype сообщает «кто говорит» только в групповых созвонах, а в звонке вдвоём
    событий нет. Зато собеседник ровно один: всё, что звучит из динамиков, пока идёт звонок, — его речь."""
    remote = [u for u, p in people.items() if not p["self"]]
    # открытым может быть и просто чат (а созвон — в Teams или Zoom), поэтому собеседником считаем только того,
    # у кого в журнале менялось состояние звука; разговоров может быть несколько — звонок должен быть один
    in_call = [u for u in remote if any(e["kind"] == "av_state" and e.get("uri") == u for e in ev)]
    if len(in_call) != 1 or any(e["kind"] == "conversation" and e.get("participants", 0) > 2 for e in ev):
        return None
    uri = in_call[0]
    states = [(e["t"], e.get("state")) for e in ev if e["kind"] == "av_state" and e.get("uri") == uri]
    begin = next((t for t, st in states if st == "Connected"), None)
    hang = next((t for t, st in states if st == "Disconnected" and (begin is None or t > begin)), None)
    a = conv(begin) if begin else 0.0
    b = min(conv(hang), duration) if hang else duration
    if b - a < 1:
        return None
    return [(round(a, 2), round(b, 2), uri)], people


# ---------- разметка ----------

def diarize(mic, system, segs: list, people: dict, user_name: str, known: list):
    """Разметка голосов по журналу Skype. Возвращает (разметка как у asr.run_diar_call, участники по номерам)."""
    from asr import _mask_segments, _speech_mask
    frame = SR // 10
    n = len(system) if mic is None else min(len(mic), len(system))
    sys_mask = _speech_mask(system[:n], frame)
    order = []                                                  # собеседники в порядке появления
    for _, _, uri in segs:
        if not people[uri]["self"] and uri not in order:
            order.append(uri)
    active = np.full(len(sys_mask), -1)
    for a, b, uri in segs:
        if uri in order:
            active[int(a * 10):int(b * 10) + 1] = order.index(uri)
    # пока Skype показывает хозяина записи, а из динамиков звучит речь — это реплика последнего собеседника
    last = next((x for x in active if x >= 0), 0)
    for i in range(len(active)):
        if active[i] >= 0:
            last = active[i]
        else:
            active[i] = last
    dia = []
    if mic is not None:
        mic_mask = _speech_mask(mic[:n], frame)
        dia += _mask_segments(mic_mask & ~sys_mask, 0.1, 0)
    for k in range(len(order)):
        dia += _mask_segments(sys_mask & (active == k), 0.1, k + 1)
    dia.sort(key=lambda x: x["s"])
    names = {}
    if mic is not None:
        me = next((u for u, p in people.items() if p["self"]), "")
        names[0] = {"name": person_name(me, "", True, user_name, known) if me else user_name, "uri": me}
    for k, uri in enumerate(order):
        names[k + 1] = {"name": person_name(uri, people[uri]["display"], False, user_name, known),
                        "uri": uri, "display": people[uri]["display"]}
    present = {x["spk"] for x in dia}
    return dia, {k: v for k, v in names.items() if k in present}
