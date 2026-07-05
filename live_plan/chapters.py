# -*- coding: utf-8 -*-
"""Group parsed trip days into 5 country/stage chapters for the postcards site."""
from __future__ import annotations

import re

from trip_parser import REGION, transport_icon

CHAPTER_DEFS: list[dict] = [
    {"id": "departure", "title": "Вылет", "day_nums": range(1, 2), "region": "travel"},
    {"id": "thailand", "title": "Таиланд", "day_nums": range(2, 11), "region": "th"},
    {"id": "vietnam", "title": "Вьетнам", "day_nums": range(11, 21), "region": "vn"},
    {"id": "china", "title": "Китай", "day_nums": range(21, 30), "region": "cn"},
]

CHAPTER_HERO: dict[str, str] = {
    "departure": "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?auto=format&fit=crop&w=900&q=60",
    "thailand": "https://images.unsplash.com/photo-1552465011-b4e21bf6e79a?auto=format&fit=crop&w=900&q=60",
    "vietnam": "https://images.unsplash.com/photo-1583417319070-4a69db38a482?auto=format&fit=crop&w=900&q=60",
    "china": "https://images.unsplash.com/photo-1474181487882-5abf3f0ba6c2?auto=format&fit=crop&w=900&q=60",
}

_GENERIC_PLACES = {"перелёт", "перелет", "поезд", "рейс", "самолёт", "самолет", "в пути"}

_HIGHLIGHT_INCLUDE = (
    "рейс", "полёт", "полет", "вылет", "посадк", "перелёт", "перелет", "прилёт", "прилет",
    "иммиграц", "поезд", "g2", "всм", "вокзал", "паром", "катер", "автобус",
    "ba na", "ба на", "golden bridge", "канатн", "disney", "будда", "buddha",
    "запретн", "forbidden", "великая стен", "мутяньюй", "храм неба", "temple of heaven",
    "канатная",
)

_HIGHLIGHT_SKIP = (
    "сон", "завтрак", "обед", "ужин", "душ", "7-eleven", "7-11", "отдых", "отбой",
    "подъём", "подъем", "свободное время", "сборы", "распаковка",
)


def assign_chapter(day_num: int) -> str:
    """Return the chapter id a given day number belongs to."""
    for chapter in CHAPTER_DEFS:
        if day_num in chapter["day_nums"]:
            return chapter["id"]
    return CHAPTER_DEFS[-1]["id"]


def sanitize_text(text: str) -> str:
    """Strip PNRs, ruble amounts and budget/estimate clauses from public text."""
    if not text:
        return ""
    cleaned = re.sub(r"PNR\s+\w+", "", text)
    cleaned = re.sub(r"~?\d[\d\s.,–—-]*₽", "", cleaned)
    parts = re.split(r"[;·]", cleaned)
    kept = [
        part for part in parts
        if "бюджет" not in part.lower() and "ориентир" not in part.lower()
    ]
    cleaned = "; ".join(part.strip() for part in kept if part.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" ;,·—-").strip()


def _clean_city(city: str) -> str:
    """Normalise a day city into a single destination name for the chip list."""
    city = re.sub(r"\s*\([^)]*\)", "", city).strip()
    if "→" in city:
        segments = [seg.strip() for seg in city.split("→")]
        segments = [
            seg for seg in segments
            if seg and seg.lower() not in _GENERIC_PLACES
        ]
        if segments:
            return segments[-1]
        return ""
    return city


def pick_chapter_highlights(days: list[dict], limit: int = 4) -> list[str]:
    """Choose a few important, sanitized events across a chapter's days."""
    highlights: list[str] = []
    seen: set[str] = set()
    for day in days:
        for step in day.get("steps", []):
            place = step.get("place", "")
            action = step.get("action", "")
            haystack = f"{place} {action}".lower()
            if any(skip in haystack for skip in _HIGHLIGHT_SKIP):
                continue
            if not any(key in haystack for key in _HIGHLIGHT_INCLUDE):
                continue
            text = sanitize_text(action) or sanitize_text(place)
            if not text:
                continue
            icon = transport_icon(haystack)
            label = f"{icon} {text}"
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            highlights.append(label)
            if len(highlights) >= limit:
                return highlights
    return highlights


def _to_iso(date: str) -> str:
    """Convert DD.MM.YYYY into YYYY-MM-DD."""
    day, month, year = date.split(".")
    return f"{year}-{month}-{day}"


def build_chapters(parsed_days: list[dict]) -> list[dict]:
    """Turn the flat list of parsed days into chapter dicts (departure + 3 route stages)."""
    by_id: dict[str, list[dict]] = {chapter["id"]: [] for chapter in CHAPTER_DEFS}
    for day in parsed_days:
        by_id[assign_chapter(day["num"])].append(day)

    chapters: list[dict] = []
    for chapter in CHAPTER_DEFS:
        days = sorted(by_id[chapter["id"]], key=lambda d: d["num"])
        if not days:
            continue
        region = chapter["region"]
        region_meta = REGION.get(region, REGION["travel"])

        cities: list[str] = []
        day_items: list[dict] = []
        for day in days:
            city = _clean_city(day["city"])
            if city and city not in cities:
                cities.append(city)
            day_items.append({
                "num": day["num"],
                "date": day["date"],
                "date_short": day["date"][:5],
                "weekday": day["weekday"],
                "city": day["city"],
            })

        first, last = days[0], days[-1]
        chapters.append({
            "id": chapter["id"],
            "title": chapter["title"],
            "region": region,
            "region_name": region_meta["name"],
            "accent": region_meta["accent"],
            "bg": region_meta["bg"],
            "hero_image": CHAPTER_HERO.get(chapter["id"], ""),
            "date_from": first["date"][:5],
            "date_to": last["date"][:5],
            "date_from_iso": _to_iso(first["date"]),
            "date_to_iso": _to_iso(last["date"]),
            "day_count": len(days),
            "cities": cities,
            "highlights": pick_chapter_highlights(days),
            "days": day_items,
        })
    return chapters


def current_chapter_id(chapters: list[dict], today_iso: str) -> str | None:
    """Return the id of the chapter whose date range contains today_iso, if any."""
    for chapter in chapters:
        if chapter["date_from_iso"] <= today_iso <= chapter["date_to_iso"]:
            return chapter["id"]
    return None
