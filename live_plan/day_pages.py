# -*- coding: utf-8 -*-
"""Helpers for building public day detail pages."""
from __future__ import annotations

import json
import re
from pathlib import Path

from live_plan.blocks import normalize_blocks
from live_plan.chapters import assign_chapter, sanitize_text
from trip_parser import REGION, transport_icon

LIVE_DIR = Path(__file__).resolve().parent
MEDIA_CONFIG_PATH = LIVE_DIR / "day_media.json"
MEDIA_SRC = LIVE_DIR / "media"

REGION_HERO = {
    "ru": {
        "url": "https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?w=900&q=80",
        "caption": "Сибирь",
    },
    "th": {
        "url": "https://images.unsplash.com/photo-1528183429752-a97d0bf99b5a?w=900&q=80",
        "caption": "Таиланд",
    },
    "vn": {
        "url": "https://images.unsplash.com/photo-1559592413-7e7a2656f235?w=900&q=80",
        "caption": "Вьетнам",
    },
    "cn": {
        "url": "https://images.unsplash.com/photo-1535354839856-604977947?w=900&q=80",
        "caption": "Китай",
    },
    "travel": {
        "url": "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=900&q=80",
        "caption": "В дороге",
    },
}

IMPORTANT_KEYWORDS = (
    "полёт", "рейс", "борту", "аэропорт", "bkk", "can", "dmk", "dad", "sgn", "pvg", "pek", "kja", "ikt",
    "поезд", "вокзал", "081", "g2", "паром", "иммиграц", "регистрац", "посадка", "прилёт", "прилет",
    "вылет", "заселен", "check-in", "check-out", "hotel", "отель", "стыковк", "пересад",
    "ba na", "floating", "zoo", "disney", "forbidden", "bund", "остров", "ко лан",
)

SKIP_KEYWORDS = (
    "сон", "завтрак", "обед", "ужин", "душ", "7-eleven", "отдых", "свободное время",
    "сборы, проверка", "покупка билета airport bus",
)


def load_day_media() -> dict:
    if not MEDIA_CONFIG_PATH.exists():
        return {}
    return json.loads(MEDIA_CONFIG_PATH.read_text(encoding="utf-8"))


def local_media_path(url: str) -> Path | None:
    if url.startswith("media/"):
        return MEDIA_SRC / url.removeprefix("media/")
    return None


def missing_media_files(day_media: dict) -> list[str]:
    """Return local photo paths referenced in day_media but missing on disk."""
    missing: list[str] = []
    for entry in day_media.values():
        for block in normalize_blocks(entry):
            if block.get("type") != "photo":
                continue
            path = local_media_path(block.get("url", ""))
            if path and not path.exists():
                missing.append(str(path.relative_to(MEDIA_SRC.parent)))
    return missing


def media_entry(day_num: int, day_media: dict) -> dict:
    return day_media.get(str(day_num), day_media.get(day_num, {}))


def step_blob(step: dict) -> str:
    return " ".join(
        step.get(key, "") for key in ("place", "action", "next", "note", "transit")
    ).lower()


def is_important_step(step: dict) -> bool:
    text = step_blob(step)
    if any(key in text for key in SKIP_KEYWORDS):
        if not any(key in text for key in (
            "рейс", "полёт", "полете", "аэропорт", "поезд", "паром", "прилёт", "прилет", "вылет", "иммиграц",
        )):
            return False
    if any(key in text for key in IMPORTANT_KEYWORDS):
        return True
    icon = transport_icon(text)
    return icon in ("✈", "🚄", "⛴", "🚌") and "grab" not in text and "сонгтео" not in text


def sanitize_step(step: dict) -> dict | None:
    action = sanitize_text(step["action"]).lower()
    place = sanitize_text(step["place"]).lower()
    if action == "сон" or (action.startswith("сон") and "отель" not in place and "hotel" not in place):
        return None
    blob = step_blob(step)
    cleaned = {
        "time": step["time"],
        "place": sanitize_text(step["place"]),
        "action": sanitize_text(step["action"]),
        "next": sanitize_text(step["next"]) if step["next"] != "—" else "",
        "transit": sanitize_text(step["transit"]) if step["transit"] != "—" else "",
        "note": sanitize_text(step["note"]),
        "icon": transport_icon(blob),
    }
    if not cleaned["place"] and not cleaned["action"]:
        return None
    return cleaned


def build_day_steps(steps: list[dict]) -> list[dict]:
    result: list[dict] = []
    for step in steps:
        cleaned = sanitize_step(step)
        if cleaned:
            result.append(cleaned)
    return result


def public_photo_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("media/"):
        return "../" + url
    return url


def public_steps(raw_steps: list[dict] | None, entry: dict | None = None) -> list[dict]:
    """Use admin overrides when present; never fall back to the guide on public pages."""
    entry = entry or {}
    if "steps" in entry:
        return build_day_steps(entry["steps"])
    return []


def public_meta(raw_day: dict, entry: dict | None = None) -> dict[str, str]:
    """Use admin overrides when present; never fall back to the guide on public pages."""
    entry = entry or {}
    if entry.get("meta"):
        from live_plan.steps import clean_meta
        return clean_meta(entry["meta"])
    return {"totals": ""}


def public_day_summary(_day: dict | None = None, _entry: dict | None = None) -> str:
    return ""


def public_day_tag(_city: str = "", _steps: list[dict] | None = None) -> str:
    return ""


def blank_public_day(day: dict, entry: dict | None = None) -> dict:
    """Metadata only — descriptive fields come from admin overrides, not the guide."""
    meta = public_meta(day, entry)
    return {
        "num": day["num"],
        "date": day["date"],
        "weekday": day["weekday"],
        "city": sanitize_text(day["city"]),
        "region": day["region"],
        "totals": meta["totals"],
        "chapter_id": assign_chapter(day["num"]),
    }


def intro_from_media(entry: dict) -> str:
    for block in normalize_blocks(entry):
        if block.get("type") == "text":
            content = sanitize_text(block.get("content", ""))
            if content:
                return content
    return sanitize_text(entry.get("intro", ""))


def photos_from_media(day_num: int, region: str, city: str, entry: dict) -> list[dict]:
    photos: list[dict] = []
    for block in normalize_blocks(entry):
        if block.get("type") != "photo" or not block.get("url"):
            continue
        photos.append({
            "url": public_photo_url(block["url"]),
            "caption": "",
        })

    for item in entry.get("photos", []):
        if isinstance(item, str):
            photos.append({"url": public_photo_url(item), "caption": ""})
        elif isinstance(item, dict) and item.get("url"):
            photos.append({
                "url": public_photo_url(item["url"]),
                "caption": item.get("caption", ""),
            })

    if not photos:
        hero = REGION_HERO.get(region, REGION_HERO["travel"])
        photos.append({
            "url": hero["url"],
            "caption": "",
        })
    return photos


def day_tag(city: str, steps: list[dict]) -> str:
    haystack = city.lower() + " " + " ".join(step_blob(step) for step in steps)
    if "ко лан" in haystack or "остров" in haystack:
        return "остров"
    if "→" in city or any(key in haystack for key in ("перелёт", "перелет", "переезд", "поезд", "рейс", "вылет", "прилёт", "прилет")):
        return "переезд"
    if any(key in haystack for key in ("пляж", "джомтьен", "jomtien", "snorkel", "сноркл")):
        return "пляж"
    if any(key in haystack for key in ("храм", " wat ", "pagoda", "экскурс")):
        return "экскурсия"
    if "свобод" in haystack:
        return "свободный день"
    if "бангкок" in haystack or "шанхай" in haystack or "пекин" in haystack or "хошимин" in haystack:
        return "город"
    return ""


def day_summary(day: dict, entry: dict) -> str:
    intro = intro_from_media(entry)
    if intro:
        return intro
    for step in day.get("steps", []):
        if not is_important_step(step):
            continue
        text = sanitize_text(step.get("action", "")) or sanitize_text(step.get("place", ""))
        if text:
            return text
    city = sanitize_text(day.get("city", ""))
    return f"День в {city}" if city else "Подробности дня"


def chapter_badges(chapter: dict) -> list[str]:
    if chapter.get("badges"):
        return list(chapter["badges"])
    badges = [f"{chapter['day_count']} дней"]
    cities = chapter.get("cities") or []
    if len(cities) > 1:
        badges.append(f"{len(cities)} города")
    island_count = sum(
        1 for day in chapter.get("days", [])
        if day.get("tag") == "остров"
    )
    if island_count:
        badges.append(f"{island_count} остров" if island_count == 1 else f"{island_count} острова")
    if cities:
        badges.append(" → ".join(cities[:3]))
    return badges


def enrich_chapter_days(chapter: dict, parsed_by_num: dict[int, dict], day_media: dict) -> None:
    for day_item in chapter.get("days", []):
        raw = parsed_by_num.get(day_item["num"], {})
        entry = media_entry(day_item["num"], day_media)
        day_item["summary"] = public_day_summary(raw, entry)
        day_item["tag"] = public_day_tag(raw.get("city", day_item["city"]), raw.get("steps", []))
        day_item["page_url"] = f"../days/{day_item['num']:02d}.html"
        day_item["chapter_id"] = chapter["id"]


def build_public_day(day: dict, day_media: dict) -> dict:
    entry = media_entry(day["num"], day_media)
    return {
        "num": day["num"],
        "date": day["date"],
        "weekday": day["weekday"],
        "city": sanitize_text(day["city"]),
        "region": day["region"],
        "night": sanitize_text(day.get("night", "")),
        "weather": sanitize_text(day.get("weather", "")),
        "totals": sanitize_text(day.get("totals", "")),
        "chapter_id": assign_chapter(day["num"]),
    }


def verify_day_output(payload: dict) -> None:
    blob = json.dumps(payload, ensure_ascii=False)
    if re.search(r"PNR\s+\w+", blob, re.I):
        raise SystemExit("Sanitization failed: PNR found in day output")
    if "₽" in blob:
        raise SystemExit("Sanitization failed: ruble amounts found in day output")
    if "бюджет" in blob.lower():
        raise SystemExit("Sanitization failed: budget references found in day output")
