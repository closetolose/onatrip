"""Block-based day content helpers."""

from __future__ import annotations


def normalize_blocks(media_entry: dict) -> list[dict]:
    if media_entry.get("blocks"):
        return media_entry["blocks"]

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
    return cleaned
