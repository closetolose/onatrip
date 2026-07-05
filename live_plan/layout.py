# -*- coding: utf-8 -*-
"""Page layout: section order, visibility and per-section CSS overrides."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

LIVE_DIR = Path(__file__).resolve().parent
LAYOUT_PATH = LIVE_DIR / "layout_settings.json"

CSS_VALUE = re.compile(
    r"^[#a-zA-Z0-9\s.,%()\-+/\"'!]*$",
)

ALLOWED_STYLE_KEYS = frozenset({
    "background",
    "background-color",
    "color",
    "padding",
    "padding-top",
    "padding-right",
    "padding-bottom",
    "padding-left",
    "margin",
    "margin-top",
    "margin-right",
    "margin-bottom",
    "margin-left",
    "border-radius",
    "font-size",
    "font-weight",
    "line-height",
    "letter-spacing",
    "max-width",
    "min-height",
    "gap",
    "box-shadow",
    "opacity",
    "text-align",
    "border",
    "border-color",
    "border-width",
    "width",
    "height",
    "object-fit",
    "flex-direction",
    "align-items",
    "justify-content",
    "grid-template-columns",
})

TILE_CHAPTER_IDS = ("thailand", "vietnam", "china")

TILE_DEFAULTS: dict[str, dict[str, str]] = {
    "thailand": {
        "face_color": "#ffffff",
        "hover_color": "#fcbd1c",
        "edge_dark": "#c99710",
        "edge_light": "#fdd550",
    },
    "vietnam": {
        "face_color": "#ffffff",
        "hover_color": "#a6dfff",
        "edge_dark": "#7fb8e5",
        "edge_light": "#c5ebff",
    },
    "china": {
        "face_color": "#ffffff",
        "hover_color": "#efe4cf",
        "edge_dark": "#d5c9ad",
        "edge_light": "#f7f2e5",
    },
}

TILE_COLOR_KEYS = ("face_color", "hover_color", "edge_dark", "edge_light")

SECTION_CATALOG: dict[str, list[dict[str, str]]] = {
    "index": [
        {"id": "tiles", "label": "Фон страницы", "selector": ".trip-main"},
    ],
    "chapter": [
        {"id": "back_link", "label": "Ссылка «К плиткам»", "selector": '[data-section="back_link"]'},
        {"id": "hero_media", "label": "Hero-фото", "selector": '[data-section="hero_media"]'},
        {"id": "hero_content", "label": "Hero-текст", "selector": '[data-section="hero_content"]'},
        {"id": "badges", "label": "Бейджи", "selector": '[data-section="badges"]'},
        {"id": "highlights", "label": "Ключевые события", "selector": '[data-section="highlights"]'},
        {"id": "timeline_title", "label": "Заголовок таймлайна", "selector": '[data-section="timeline_title"]'},
        {"id": "day_timeline", "label": "Карточки дней", "selector": '[data-section="day_timeline"]'},
    ],
    "day": [
        {"id": "back_link", "label": "Ссылка «К маршруту»", "selector": '[data-section="back_link"]'},
        {"id": "hero", "label": "Hero дня", "selector": '[data-section="hero"]'},
        {"id": "gallery", "label": "Галерея фото", "selector": '[data-section="gallery"]'},
        {"id": "intro", "label": "Блок «О дне»", "selector": '[data-section="intro"]'},
        {"id": "totals", "label": "Итого", "selector": '[data-section="totals"]'},
        {"id": "pager", "label": "Навигация между днями", "selector": '[data-section="pager"]'},
    ],
}


def _default_sections(page: str) -> list[dict[str, Any]]:
    return [
        {"id": item["id"], "enabled": True, "order": index, "styles": {}}
        for index, item in enumerate(SECTION_CATALOG[page])
    ]


DEFAULT_LAYOUT: dict[str, Any] = {
    "pages": {
        page: {"sections": _default_sections(page)}
        for page in SECTION_CATALOG
    },
    "tiles": {},
    "custom_rules": [],
}


def deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def sanitize_styles(styles: dict | None) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in (styles or {}).items():
        prop = str(key).strip().lower()
        if prop not in ALLOWED_STYLE_KEYS:
            continue
        text = str(value).strip()
        if not text or not CSS_VALUE.match(text):
            continue
        if "url(" in text.lower() and "javascript:" in text.lower():
            continue
        cleaned[prop] = text
    return cleaned


def sanitize_sections(page: str, sections: list | None) -> list[dict[str, Any]]:
    catalog_ids = [item["id"] for item in SECTION_CATALOG[page]]
    by_id: dict[str, dict[str, Any]] = {}
    for raw in sections or []:
        if not isinstance(raw, dict):
            continue
        section_id = str(raw.get("id", "")).strip()
        if section_id not in catalog_ids:
            continue
        by_id[section_id] = {
            "id": section_id,
            "enabled": bool(raw.get("enabled", True)),
            "order": int(raw.get("order", catalog_ids.index(section_id))),
            "styles": sanitize_styles(raw.get("styles")),
        }
    result: list[dict[str, Any]] = []
    for index, section_id in enumerate(catalog_ids):
        entry = by_id.get(section_id, {
            "id": section_id,
            "enabled": True,
            "order": index,
            "styles": {},
        })
        entry["order"] = index if section_id not in by_id else entry["order"]
        result.append(entry)
    result.sort(key=lambda item: item["order"])
    for index, entry in enumerate(result):
        entry["order"] = index
    return result


def sanitize_layout(data: dict | None) -> dict[str, Any]:
    merged = deep_merge(DEFAULT_LAYOUT, data if isinstance(data, dict) else {})
    pages: dict[str, Any] = {}
    for page in SECTION_CATALOG:
        page_data = merged.get("pages", {}).get(page, {})
        pages[page] = {
            "sections": sanitize_sections(page, page_data.get("sections")),
        }
    tiles = merged.get("tiles", {})
    clean_tiles: dict[str, Any] = {}
    if isinstance(tiles, dict):
        for chapter_id, tile in tiles.items():
            if not isinstance(tile, dict):
                continue
            entry: dict[str, Any] = {
                "label": str(tile.get("label", "")).strip(),
                "icon": str(tile.get("icon", "")).strip(),
                "visible": bool(tile.get("visible", True)),
            }
            for color_key in TILE_COLOR_KEYS:
                value = str(tile.get(color_key, "")).strip()
                if value:
                    entry[color_key] = value
            clean_tiles[str(chapter_id)] = entry
    return {"pages": pages, "tiles": clean_tiles, "custom_rules": sanitize_custom_rules(merged.get("custom_rules"))}


def sanitize_custom_rules(rules: list | None) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for raw in rules or []:
        if not isinstance(raw, dict):
            continue
        selector = str(raw.get("selector", "")).strip()
        if not selector or len(selector) > 240:
            continue
        if any(bad in selector.lower() for bad in ("javascript:", "<", ">", "{", "}")):
            continue
        styles = sanitize_styles(raw.get("styles"))
        if not styles:
            continue
        cleaned.append({
            "selector": selector,
            "label": str(raw.get("label", "")).strip(),
            "page": str(raw.get("page", "")).strip(),
            "styles": styles,
        })
    return cleaned


def load_layout() -> dict[str, Any]:
    stored: dict[str, Any] = {}
    if LAYOUT_PATH.exists():
        stored = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    return sanitize_layout(stored)


def save_layout(data: dict[str, Any]) -> dict[str, Any]:
    cleaned = sanitize_layout(data)
    LAYOUT_PATH.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return cleaned


def section_map(page: str, layout: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    layout = layout or load_layout()
    sections = layout.get("pages", {}).get(page, {}).get("sections", [])
    return {item["id"]: item for item in sections}


def is_enabled(page: str, section_id: str, layout: dict[str, Any] | None = None) -> bool:
    section = section_map(page, layout).get(section_id)
    return bool(section.get("enabled", True)) if section else True


def effective_tile(chapter_id: str, override: dict[str, Any] | None = None) -> dict[str, str]:
    defaults = TILE_DEFAULTS.get(chapter_id, TILE_DEFAULTS["china"])
    override = override if isinstance(override, dict) else {}
    result = dict(defaults)
    for color_key in TILE_COLOR_KEYS:
        value = str(override.get(color_key, "")).strip()
        if value:
            result[color_key] = value
    return result


def render_tile_css(layout: dict[str, Any] | None = None) -> str:
    layout = layout or load_layout()
    tiles = layout.get("tiles") or {}
    lines = ["/* Tile colors — edit in admin → Макет or Визуально */"]
    for chapter_id in TILE_CHAPTER_IDS:
        colors = effective_tile(chapter_id, tiles.get(chapter_id))
        link = f'.tile-link[data-tile-id="{chapter_id}"]'
        base = f"body.index-page .social-tiles {link}"
        hover_link = (
            f"body.index-page .social-tiles .tile:hover {link}, "
            f"body.index-page .social-tiles {link}:focus-visible"
        )
        lines.append(f"{base} {{ background: {colors['face_color']}; }}")
        lines.append(f"{base}::before {{ background: {colors['edge_dark']}; }}")
        lines.append(f"{base}::after {{ background: {colors['edge_light']}; }}")
        lines.append(f"{hover_link} {{ background: {colors['hover_color']}; }}")
    return "\n".join(lines)


def render_layout_css(layout: dict[str, Any] | None = None) -> str:
    layout = layout or load_layout()
    lines = [
        "/* Generated layout overrides — edit in admin → Макет */",
    ]
    for page, catalog in SECTION_CATALOG.items():
        sections = section_map(page, layout)
        for item in catalog:
            section = sections.get(item["id"], {})
            selector = item["selector"]
            if not section.get("enabled", True):
                lines.append(f"{selector} {{ display: none !important; }}")
                continue
            styles = section.get("styles") or {}
            if not styles:
                continue
            lines.append(f"{selector} {{")
            for prop, value in styles.items():
                lines.append(f"  {prop}: {value};")
            lines.append("}")
        page_root = {
            "index": "body.index-page",
            "chapter": "body.chapter-body",
            "day": "body.day-body",
        }[page]
        ordered = sorted(
            layout.get("pages", {}).get(page, {}).get("sections", []),
            key=lambda item: item.get("order", 0),
        )
        if ordered:
            lines.append(f"{page_root} {{ display: flex; flex-direction: column; }}")
            lines.append(f"{page_root} > main {{ display: flex; flex-direction: column; }}")
            for section in ordered:
                catalog_item = next(
                    (item for item in catalog if item["id"] == section["id"]),
                    None,
                )
                if not catalog_item:
                    continue
                lines.append(
                    f'{page_root} {catalog_item["selector"]} {{ order: {section["order"]}; }}'
                )
    for rule in layout.get("custom_rules") or []:
        selector = rule.get("selector")
        styles = rule.get("styles") or {}
        if not selector or not styles:
            continue
        page = str(rule.get("page", "")).strip()
        if page == "index" and not selector.startswith("body."):
            selector = f"body.index-page {selector}"
        lines.append(f"{selector} {{")
        for prop, value in styles.items():
            lines.append(f"  {prop}: {value};")
        lines.append("}")
    lines.append(render_tile_css(layout))
    return "\n".join(lines) + "\n"


def admin_schema() -> dict[str, Any]:
    return {
        "pages": {
            page: {
                "title": {
                    "index": "Главная (плитки)",
                    "chapter": "Страница главы",
                    "day": "Страница дня",
                }[page],
                "sections": [
                    {
                        "id": item["id"],
                        "label": item["label"],
                        **next(
                            (
                                {
                                    "enabled": section["enabled"],
                                    "order": section["order"],
                                    "styles": section["styles"],
                                }
                                for section in load_layout()["pages"][page]["sections"]
                                if section["id"] == item["id"]
                            ),
                            {"enabled": True, "order": index, "styles": {}},
                        ),
                    }
                    for index, item in enumerate(SECTION_CATALOG[page])
                ],
            }
            for page in SECTION_CATALOG
        },
        "style_keys": sorted(ALLOWED_STYLE_KEYS),
        "sections_catalog": SECTION_CATALOG,
        "tile_defaults": TILE_DEFAULTS,
        "tile_chapters": list(TILE_CHAPTER_IDS),
    }
