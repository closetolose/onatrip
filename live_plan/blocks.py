"""Block-based day content helpers."""

from __future__ import annotations


def normalize_blocks(media_entry: dict) -> list[dict]:
    if "blocks" in media_entry:
        return media_entry["blocks"] or []

    blocks: list[dict] = []
    intro = (media_entry.get("intro") or "").strip()
    if intro:
        blocks.append({"type": "text", "content": intro})

    for item in media_entry.get("photos", []):
        if isinstance(item, str):
            blocks.append({"type": "photo", "url": item, "caption": ""})
        elif isinstance(item, dict) and item.get("url"):
            blocks.append({
                "type": "photo",
                "url": item["url"],
                "caption": item.get("caption", ""),
            })
    return blocks


def _clean_photo_item(item) -> dict | None:
    if isinstance(item, str) and item.strip():
        return {"url": item.strip(), "caption": ""}
    if isinstance(item, dict) and item.get("url"):
        return {
            "url": item["url"],
            "caption": (item.get("caption") or "").strip(),
        }
    return None


def clean_blocks(blocks: list) -> list[dict]:
    cleaned: list[dict] = []
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "text":
            content = (block.get("content") or "").strip()
            if content:
                cleaned.append({"type": "text", "content": content})
        elif block_type == "photo" and block.get("url"):
            cleaned.append({
                "type": "photo",
                "url": block["url"],
                "caption": (block.get("caption") or "").strip(),
            })
        elif block_type == "carousel":
            photos: list[dict] = []
            for item in block.get("photos", []):
                photo = _clean_photo_item(item)
                if photo:
                    photos.append(photo)
            if photos:
                cleaned.append({"type": "carousel", "photos": photos})
        elif block_type == "side":
            url = str(block.get("url", "")).strip()
            content = (block.get("content") or "").strip()
            side = block.get("side", "left")
            if side not in ("left", "right"):
                side = "left"
            if url or content:
                cleaned.append({
                    "type": "side",
                    "side": side,
                    "url": url,
                    "caption": (block.get("caption") or "").strip(),
                    "content": content,
                })
    return cleaned


HERO_FIELDS = ("eyebrow", "title", "meta")


def clean_hero(hero: dict | None) -> dict:
    hero = hero or {}
    return {
        "eyebrow": (hero.get("eyebrow") or "").strip(),
        "title": (hero.get("title") or "").strip(),
        "meta": (hero.get("meta") or "").strip(),
    }
