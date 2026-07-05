# -*- coding: utf-8 -*-
"""Shared parser for trip markdown guides."""
import re
from datetime import datetime

ROUTE = [
    ("28.07", "KJA", "Красноярск", "ru"),
    ("29.07", "BKK", "Паттайя", "th"),
    ("05.08", "DMK", "Бангкок", "th"),
    ("07.08", "DAD", "Да Нанг", "vn"),
    ("14.08", "SGN", "Хошимин", "vn"),
    ("17.08", "PVG", "Шанхай", "cn"),
    ("21.08", "PEK", "Пекин", "cn"),
    ("24.08", "IKT", "Иркутск", "ru"),
    ("25.08", "KJA", "Домой", "ru"),
]

MAP_NODES = [
    ("KJA", 56.17, 92.49),
    ("BKK", 12.93, 100.88),
    ("DMK", 13.91, 100.61),
    ("DAD", 16.04, 108.20),
    ("SGN", 10.82, 106.65),
    ("PVG", 31.14, 121.81),
    ("PEK", 40.08, 116.60),
    ("IKT", 52.27, 104.39),
    ("KJA", 56.17, 92.49),
]

REGION = {
    "ru": {"name": "Россия", "color": "#23212c", "bg": "#e3d5bc", "accent": "#006434"},
    "th": {"name": "Таиланд", "color": "#23212c", "bg": "#fcbd1c", "accent": "#23212c"},
    "vn": {"name": "Вьетнам", "color": "#23212c", "bg": "#a6dfff", "accent": "#23212c"},
    "cn": {"name": "Китай", "color": "#23212c", "bg": "#efe4cf", "accent": "#006434"},
    "travel": {"name": "Переезд", "color": "#23212c", "bg": "#ddd0b4", "accent": "#23212c"},
}


def _parse_day_date(date_str: str) -> datetime:
    if "-" in date_str and len(date_str) >= 10:
        return datetime.strptime(date_str[:10], "%Y-%m-%d")
    parts = date_str.split(".")
    if len(parts) == 3:
        d, m, y = parts
        return datetime(int(y), int(m), int(d))
    raise ValueError(f"Unsupported date format: {date_str!r}")


def _parse_route_date(dd_mm: str, year: int) -> datetime:
    d, m = dd_mm.split(".")
    return datetime(year, int(m), int(d))


def waypoint_for_date(day_date_str: str, route=ROUTE) -> int:
    """Return index of the latest route node whose date is on or before day_date_str."""
    day_dt = _parse_day_date(day_date_str)
    best_idx = 0
    for idx, (date_str, *_rest) in enumerate(route):
        route_dt = _parse_route_date(date_str, day_dt.year)
        if route_dt <= day_dt:
            best_idx = idx
    return best_idx


def detect_region(city: str, title: str) -> str:
    t = (city + " " + title).lower()
    if any(x in t for x in ("красноярск", "иркутск", "поезд →", "домой", "перелёт", "→")):
        if "паттайя" in t or "бангкок" in t:
            pass
        elif "хойан" in t or "дананг" in t or "хошимин" in t:
            pass
        elif "шанхай" in t or "пекин" in t:
            pass
        elif "иркутск" in t or "красноярск" in t or "домой" in t:
            return "ru"
        elif "перелёт" in t or "→" in city:
            return "travel"
    if any(x in t for x in ("паттайя", "бангкок", "тай")):
        return "th"
    if any(x in t for x in ("хойан", "дананг", "хошимин", "вьетнам")):
        return "vn"
    if any(x in t for x in ("шанхай", "пекин", "китай")):
        return "cn"
    if "перелёт" in t or "переезд" in t or "→" in t:
        return "travel"
    return "travel"


def transport_icon(text: str) -> str:
    t = text.lower()
    if "полёт" in t or "рейс" in t or "борту" in t or "аэропорт" in t or "bkk" in t or "can" in t:
        return "✈"
    if "поезд" in t or "вокзал" in t or "081" in t or "g2" in t:
        return "🚄"
    if "метро" in t or "bts" in t or "mrt" in t or "линия" in t:
        return "🚇"
    if "grab" in t or "такси" in t or "didi" in t:
        return "🚗"
    if "паром" in t or "лодк" in t:
        return "⛴"
    if "автобус" in t or "сонгтео" in t:
        return "🚌"
    if "пешком" in t:
        return "🚶"
    if "сон" in t:
        return "🌙"
    if "пляж" in t or "остров" in t or "ко лан" in t:
        return "🏖"
    if "храм" in t or "wat" in t or "pagoda" in t:
        return "⛩"
    if "тц" in t or "terminal" in t or "mall" in t or "шопинг" in t:
        return "🛍"
    if "disney" in t:
        return "🎢"
    return "📍"


def parse_md(text: str) -> dict:
    days = []
    critical = []

    chunks = re.split(r"\n(?=## )", text)
    for chunk in chunks:
        if chunk.startswith("## Критические"):
            lines = chunk.split("\n")[1:]
            for line in lines:
                m = re.match(r"^\d+\.\s+\*\*(.+?)\*\*:\s*(.+)$", line.strip())
                if m:
                    critical.append((m.group(1), m.group(2)))
            continue
        m = re.match(
            r"## День (\d+) — (\d{2}\.\d{2}\.\d{4}) \(([^)]+)\) · (.+)",
            chunk,
        )
        if not m:
            continue
        day_num, date, weekday, city = m.groups()
        night = weather = totals = ""
        steps = []

        for line in chunk.split("\n"):
            line = line.strip()
            if line.startswith("**Ночёвка:**"):
                night = line.replace("**Ночёвка:**", "").strip()
            elif line.startswith("**Погода/запас:**"):
                weather = line.replace("**Погода/запас:**", "").strip()
            elif line.startswith("**Итого дня:**"):
                totals = line.replace("**Итого дня:**", "").strip()
            elif line.startswith("|") and not line.startswith("| Время") and not line.startswith("|-"):
                cols = [c.strip() for c in line.strip("|").split("|")]
                if len(cols) >= 7 and cols[0] != "Время":
                    steps.append({
                        "time": cols[0],
                        "place": cols[1],
                        "action": cols[2],
                        "duration": cols[3],
                        "next": cols[4],
                        "transit": cols[5],
                        "note": cols[6],
                    })

        region = detect_region(city, city)
        days.append({
            "num": int(day_num),
            "date": date,
            "weekday": weekday,
            "city": city,
            "region": region,
            "night": night,
            "weather": weather,
            "totals": totals,
            "steps": steps,
        })
    return {"days": days, "critical": critical}
