# -*- coding: utf-8 -*-
"""Karl globe chapter copy — original karlgonsalves.com text slots + per-country presets."""

from __future__ import annotations

from typing import Any

# Exact strings from karlgonsalves.com (index.template.html)
KARL_ORIGINAL_TEXT: dict[str, str] = {
    "nav_home": "HOME",
    "nav_route": "ABOUT",
    "nav_main": "WORK",
    "nav_play": "PLAY",
    "nav_contact": "CONTACT",
    "panel_a": "Let's\nroll..",
    "panel_b_a": "I'm Karl,",
    "panel_b_b": "a motion designer.",
    "panel_c_before": "Visit my page on",
    "panel_c_after": "for my latest work.",
    "panel_d_b": "I dabble in\nweb design too",
    "panel_d_c": ".. sometimes.",
    "panel_e_c": "Let's talk!",
    "panel_e_b": "phone or email",
}

KARL_TEXT_KEYS = tuple(KARL_ORIGINAL_TEXT.keys())

KARL_COLOR_KEYS = ("sky", "globe", "ink", "text_on_globe", "text_on_sky")

# Original karlgonsalves.com palette
KARL_ORIGINAL_COLORS: dict[str, str] = {
    "sky": "#ffe100",
    "globe": "#007fff",
    "ink": "#333333",
    "text_on_globe": "#ffffff",
    "text_on_sky": "#333333",
}

CHAPTER_KARL_COLOR_PRESETS: dict[str, dict[str, str]] = {
    "thailand": {
        "sky": "#ffe600",
        "globe": "#007fff",
        "ink": "#333333",
        "text_on_globe": "#ffffff",
        "text_on_sky": "#333333",
    },
    "vietnam": {
        "sky": "#b8e8ff",
        "globe": "#006434",
        "ink": "#333333",
        "text_on_globe": "#ffffff",
        "text_on_sky": "#333333",
    },
    "china": {
        "sky": "#efe4cf",
        "globe": "#c8102e",
        "ink": "#333333",
        "text_on_globe": "#ffffff",
        "text_on_sky": "#333333",
    },
}

# Suggested defaults per travel chapter (admin placeholders / first build)
CHAPTER_KARL_PRESETS: dict[str, dict[str, str]] = {
    "thailand": {
        "nav_home": "СТАРТ",
        "nav_route": "МАРШРУТ",
        "nav_main": "ГЛАВНОЕ",
        "nav_play": "ЕЩЁ",
        "nav_contact": "ИТОГ",
        "panel_a": "Поехали\nв Таиланд..",
        "panel_b_a": "Таиланд,",
        "panel_b_b": "семейный маршрут",
        "panel_c_before": "Бангкок",
        "panel_c_after": "Чиангмай · Пхукет",
        "panel_d_b": "Пляжи · храмы",
        "panel_d_c": "тропики",
        "panel_e_c": "9 дн.",
        "panel_e_b": "листай к дням",
    },
    "vietnam": {
        "nav_home": "СТАРТ",
        "nav_route": "МАРШРУТ",
        "nav_main": "ГЛАВНОЕ",
        "nav_play": "ЕЩЁ",
        "nav_contact": "ИТОГ",
        "panel_a": "Поехали\nво Вьетнам..",
        "panel_b_a": "Вьетнам,",
        "panel_b_b": "семейный маршрут",
        "panel_c_before": "Ханой",
        "panel_c_after": "Дананг · Хошимин",
        "panel_d_b": "Золотой мост",
        "panel_d_c": "побережье",
        "panel_e_c": "9 дней",
        "panel_e_b": "листай к дням",
    },
    "china": {
        "nav_home": "СТАРТ",
        "nav_route": "МАРШРУТ",
        "nav_main": "ГЛАВНОЕ",
        "nav_play": "ЕЩЁ",
        "nav_contact": "ИТОГ",
        "panel_a": "Поехали\nв Китай..",
        "panel_b_a": "Китай,",
        "panel_b_b": "семейный маршрут",
        "panel_c_before": "Пекин",
        "panel_c_after": "Шанхай · Сиань",
        "panel_d_b": "Бунд · дворцы",
        "panel_d_c": "скоростные поезда",
        "panel_e_c": "10 дней",
        "panel_e_b": "листай к дням",
    },
}

# Diorama chapter (departure) visual tokens — Karl chapters ignore these
CHAPTER_VIBES: dict[str, dict[str, str]] = {
    "departure": {
        "sky": "#e3d5bc",
        "globe": "#007fff",
        "accent_art": "#333333",
        "ink": "#333333",
        "text_on_globe": "#ffffff",
        "text_on_sky": "#333333",
        "tagline": "Старт маршрута",
        "hero_rotate": "0",
        "sign_rotate": "0",
    },
}

DEFAULT_VIBE = CHAPTER_VIBES["departure"]


def _pick(override: dict[str, Any], key: str, fallback: str) -> str:
    raw = override.get(key, "")
    text = str(raw).strip() if raw is not None else ""
    return text if text else fallback


def karl_colors(chapter_id: str, media: dict[str, Any] | None = None) -> dict[str, str]:
    colors = dict(KARL_ORIGINAL_COLORS)
    colors.update(CHAPTER_KARL_COLOR_PRESETS.get(chapter_id, {}))

    if media:
        entry = media.get(chapter_id) if isinstance(media.get(chapter_id), dict) else {}
        karl = entry.get("karl") if isinstance(entry, dict) else {}
        if isinstance(karl, dict):
            for key in KARL_COLOR_KEYS:
                if key in karl:
                    colors[key] = _pick(karl, key, colors[key])

    return colors


def karl_texts(chapter_id: str, media: dict[str, Any] | None = None) -> dict[str, str]:
    """Resolved copy for a Karl chapter: original → country preset → admin override."""
    texts = dict(KARL_ORIGINAL_TEXT)
    texts.update(CHAPTER_KARL_PRESETS.get(chapter_id, {}))

    if media:
        entry = media.get(chapter_id) if isinstance(media.get(chapter_id), dict) else {}
        karl = entry.get("karl") if isinstance(entry, dict) else {}
        if isinstance(karl, dict):
            for key in KARL_TEXT_KEYS:
                if key in karl:
                    texts[key] = _pick(karl, key, texts[key])

    return texts


def karl_defaults_for_admin(chapter_id: str) -> dict[str, str]:
    texts = dict(KARL_ORIGINAL_TEXT)
    texts.update(CHAPTER_KARL_PRESETS.get(chapter_id, {}))
    colors = dict(KARL_ORIGINAL_COLORS)
    colors.update(CHAPTER_KARL_COLOR_PRESETS.get(chapter_id, {}))
    return {**texts, **colors}


def chapter_vibe(chapter_id: str, media: dict[str, Any] | None = None) -> dict[str, str]:
    """Visual tokens for diorama chapters; Karl chapters use karl_texts() for copy."""
    base = dict(CHAPTER_VIBES.get(chapter_id, DEFAULT_VIBE))
    if chapter_id in CHAPTER_KARL_PRESETS:
        base.update(karl_texts(chapter_id, media))
    return base
