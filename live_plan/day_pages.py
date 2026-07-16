# -*- coding: utf-8 -*-
"""Helpers for building public day detail pages."""
from __future__ import annotations

import json
import re
from pathlib import Path

from live_plan.blocks import clean_hero, normalize_blocks
from live_plan.chapters import assign_chapter, sanitize_text
from trip_parser import REGION, transport_icon

LIVE_DIR = Path(__file__).resolve().parent
MEDIA_CONFIG_PATH = LIVE_DIR / "day_media.json"
MEDIA_SRC = LIVE_DIR / "media"

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
            if block.get("type") == "photo":
                path = local_media_path(block.get("url", ""))
                if path and not path.exists():
                    missing.append(str(path.relative_to(MEDIA_SRC.parent)))
            elif block.get("type") == "carousel":
                for item in block.get("photos", []):
                    if isinstance(item, dict):
                        path = local_media_path(item.get("url", ""))
                        if path and not path.exists():
                            missing.append(str(path.relative_to(MEDIA_SRC.parent)))
            elif block.get("type") == "side":
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


def public_day_summary(_day: dict | None = None, _entry: dict | None = None) -> str:
    return ""


def public_day_tag(_city: str = "", _steps: list[dict] | None = None) -> str:
    return ""


def hero_meta(day: dict) -> str:
    """Canonical hero meta: `{date_short} · {weekday}`."""
    date = day.get("date", "")
    date_short = date[:5] if len(date) >= 5 else date
    weekday = day.get("weekday", "")
    return f"{date_short} · {weekday}".strip(" ·")


def default_hero(day: dict, region_name: str) -> dict[str, str]:
    return {
        "eyebrow": f"День {day.get('num', '')} · {region_name}".strip(" ·"),
        "title": sanitize_text(day.get("city", "")),
        "meta": hero_meta(day),
    }


def hero_from_entry(entry: dict, day: dict, region_name: str) -> dict[str, str]:
    defaults = default_hero(day, region_name)
    saved = clean_hero(entry.get("hero"))
    if "hero" not in entry or not any(saved.values()):
        return defaults
    return {
        "eyebrow": saved["eyebrow"] or defaults["eyebrow"],
        "title": saved["title"] or defaults["title"],
        "meta": hero_meta(day),
    }


def blank_public_day(day: dict, entry: dict | None = None, region_name: str = "") -> dict:
    """Trip shell + hero text from admin (with guide defaults when fields are empty)."""
    entry = entry or {}
    hero = hero_from_entry(entry, day, region_name)
    return {
        "num": day["num"],
        "date": day["date"],
        "weekday": day["weekday"],
        "city": hero["title"],
        "region": day["region"],
        "chapter_id": assign_chapter(day["num"]),
        "hero_eyebrow": hero["eyebrow"],
        "hero_title": hero["title"],
        "hero_meta": hero["meta"],
    }


def intro_from_media(entry: dict) -> str:
    for block in normalize_blocks(entry):
        if block.get("type") == "text":
            content = sanitize_text(block.get("content", ""))
            if content:
                return content
    return ""


def _public_photo_block(block: dict) -> dict:
    return {
        "type": "photo",
        "url": public_photo_url(block["url"]),
        "caption": sanitize_text(block.get("caption", "")),
    }


def dedupe_cover_photo(blocks: list[dict], cover_url: str) -> list[dict]:
    """Drop the first photo block when it duplicates the hero cover."""
    if not cover_url or not blocks:
        return blocks
    for index, block in enumerate(blocks):
        if block.get("type") == "photo":
            if block.get("url") == cover_url:
                return blocks[:index] + blocks[index + 1 :]
            break
        if block.get("type") == "carousel":
            photos = block.get("photos") or []
            if photos and photos[0].get("url") == cover_url:
                if len(photos) == 1:
                    return blocks[:index] + blocks[index + 1 :]
                trimmed = dict(block)
                trimmed["photos"] = photos[1:]
                return blocks[:index] + [trimmed] + blocks[index + 1 :]
            break
    return blocks


def public_blocks(day_num: int, region: str, city: str, entry: dict) -> list[dict]:
    """Ordered longread blocks for the public day page."""
    result: list[dict] = []
    for block in normalize_blocks(entry):
        block_type = block.get("type")
        if block_type == "text":
            content = sanitize_text(block.get("content", ""))
            if content:
                result.append({"type": "text", "content": content})
        elif block_type == "photo" and block.get("url"):
            result.append(_public_photo_block(block))
        elif block_type == "carousel":
            photos: list[dict] = []
            for item in block.get("photos", []):
                if isinstance(item, dict) and item.get("url"):
                    photos.append(_public_photo_block(item))
            if photos:
                result.append({"type": "carousel", "photos": photos})
        elif block_type == "side":
            url = str(block.get("url", "")).strip()
            content = sanitize_text(block.get("content", ""))
            side = block.get("side", "left")
            if side not in ("left", "right"):
                side = "left"
            if not url and not content:
                continue
            result.append({
                "type": "side",
                "side": side,
                "url": public_photo_url(url) if url else "",
                "caption": sanitize_text(block.get("caption", "")),
                "content": content,
            })
        elif block_type == "section":
            kicker = sanitize_text(block.get("kicker", ""))
            title = sanitize_text(block.get("title", ""))
            content = sanitize_text(block.get("content", ""))
            if not kicker and not title and not content:
                continue
            result.append({
                "type": "section",
                "kicker": kicker,
                "title": title,
                "content": content,
            })

    return result


def public_blocks_with_cover(
    day_num: int,
    region: str,
    city: str,
    entry: dict,
) -> tuple[list[dict], str]:
    """Public blocks plus hero cover URL (deduped against the same cover)."""
    blocks = public_blocks(day_num, region, city, entry)
    cover = cover_image_url(entry, blocks)
    return dedupe_cover_photo(blocks, cover), cover


def is_story_empty(blocks: list[dict]) -> bool:
    return not blocks


def cover_image_url(entry: dict, blocks: list[dict]) -> str:
    """Hero cover: explicit hero.cover or first photo in blocks."""
    hero = entry.get("hero") or {}
    explicit = str(hero.get("cover") or hero.get("cover_url") or "").strip()
    if explicit:
        return public_photo_url(explicit)
    for block in blocks:
        if block.get("type") == "photo" and block.get("url"):
            return block["url"]
        if block.get("type") == "carousel":
            photos = block.get("photos") or []
            if photos and photos[0].get("url"):
                return photos[0]["url"]
        if block.get("type") == "side" and block.get("url"):
            return block["url"]
    return ""


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
