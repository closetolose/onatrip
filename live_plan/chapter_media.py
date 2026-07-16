# -*- coding: utf-8 -*-
"""Per-chapter content overrides editable from admin."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

LIVE_DIR = Path(__file__).resolve().parent
CHAPTER_MEDIA_PATH = LIVE_DIR / "chapter_media.json"

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

DEFAULT_ENTRY: dict[str, Any] = {
    "title": "",
    "description": "",
    "hero_image": "",
    "page_bg": "",
    "badges": [],
    "highlights": [],
    "day_overrides": {},
    "karl": {},
}

from live_plan.chapter_vibes import KARL_COLOR_KEYS, KARL_TEXT_KEYS, chapter_vibe, karl_colors

KARL_KEYS = KARL_TEXT_KEYS + KARL_COLOR_KEYS


def _sanitize_karl(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for key in KARL_KEYS:
        value = str(raw.get(key, "")).strip()
        if not value:
            continue
        if key in KARL_COLOR_KEYS:
            if HEX_COLOR.match(value):
                result[key] = value
            continue
        result[key] = value[:300]
    return result


def _sanitize_hex_color(value: Any) -> str:
    text = str(value or "").strip()
    return text if HEX_COLOR.match(text) else ""


def load_chapter_media() -> dict[str, Any]:
    if not CHAPTER_MEDIA_PATH.exists():
        return {}
    return json.loads(CHAPTER_MEDIA_PATH.read_text(encoding="utf-8"))


def save_chapter_media(data: dict[str, Any]) -> dict[str, Any]:
    cleaned = sanitize_chapter_media(data)
    CHAPTER_MEDIA_PATH.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return cleaned


def sanitize_chapter_media(data: dict | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for chapter_id, raw in (data or {}).items():
        if not isinstance(raw, dict):
            continue
        entry = deepcopy(DEFAULT_ENTRY)
        entry["title"] = str(raw.get("title", "")).strip()
        entry["description"] = str(raw.get("description", "")).strip()
        entry["hero_image"] = str(raw.get("hero_image", "")).strip()
        entry["page_bg"] = _sanitize_hex_color(raw.get("page_bg", ""))
        entry["badges"] = [
            str(item).strip()
            for item in raw.get("badges", [])
            if str(item).strip()
        ]
        entry["highlights"] = [
            str(item).strip()
            for item in raw.get("highlights", [])
            if str(item).strip()
        ]
        overrides: dict[str, Any] = {}
        for day_key, day_raw in (raw.get("day_overrides") or {}).items():
            if not isinstance(day_raw, dict):
                continue
            overrides[str(day_key)] = {
                key: str(day_raw.get(key, "")).strip()
                for key in ("summary", "tag", "city")
                if str(day_raw.get(key, "")).strip()
            }
        entry["day_overrides"] = overrides
        entry["karl"] = _sanitize_karl(raw.get("karl"))
        if any([
            entry["title"],
            entry["description"],
            entry["hero_image"],
            entry["page_bg"],
            entry["badges"],
            entry["highlights"],
            entry["day_overrides"],
            entry["karl"],
        ]):
            result[str(chapter_id)] = entry
    return result


def chapter_entry(chapter_id: str, media: dict[str, Any] | None = None) -> dict[str, Any]:
    media = media if media is not None else load_chapter_media()
    entry = deepcopy(DEFAULT_ENTRY)
    stored = media.get(chapter_id)
    if isinstance(stored, dict):
        entry.update(stored)
    entry["page_bg"] = _sanitize_hex_color(entry.get("page_bg", ""))
    entry["karl"] = _sanitize_karl(entry.get("karl"))
    return entry


def public_image_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("media/"):
        return "../" + url
    return url


def day_page_vibe(chapter_id: str, media: dict[str, Any] | None = None) -> dict[str, str]:
    """Sky / ink / globe tokens for NYT day pages (Karl + diorama chapters)."""
    from live_plan.karl_index import KARL_CHAPTER_IDS

    if chapter_id in KARL_CHAPTER_IDS:
        colors = karl_colors(chapter_id, media)
        return {"sky": colors["sky"], "ink": colors["ink"], "globe": colors["globe"]}
    vibe = chapter_vibe(chapter_id, media)
    return {"sky": vibe["sky"], "ink": vibe["ink"], "globe": vibe["globe"]}


def apply_chapter_overrides(chapter: dict, media: dict[str, Any] | None = None) -> dict:
    entry = chapter_entry(chapter["id"], media)
    result = deepcopy(chapter)
    if entry["title"]:
        result["title"] = entry["title"]
    if entry["description"]:
        result["description"] = entry["description"]
    if entry["hero_image"]:
        result["hero_image"] = public_image_url(entry["hero_image"])
    if entry["page_bg"]:
        result["page_bg"] = entry["page_bg"]
    if entry["badges"]:
        result["badges"] = entry["badges"]
    if entry["highlights"]:
        result["highlights"] = entry["highlights"]
    overrides = entry.get("day_overrides") or {}
    days = []
    for day in result.get("days", []):
        day_copy = deepcopy(day)
        override = overrides.get(str(day["num"]), {})
        for key in ("summary", "tag", "city"):
            if override.get(key):
                day_copy[key] = override[key]
        days.append(day_copy)
    result["days"] = days
    result["day_vibe"] = day_page_vibe(chapter["id"], media)
    return result
