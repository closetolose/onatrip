"""Site-wide settings: meta, copy, theme, custom CSS."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

LIVE_DIR = Path(__file__).resolve().parent
SETTINGS_PATH = LIVE_DIR / "site_settings.json"
CONFIG_PATH = LIVE_DIR / "config.json"

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

DEFAULTS: dict[str, Any] = {
    "meta": {
        "traveler": "Путешественник",
        "period": "",
        "period_start": "",
        "period_end": "",
        "subtitle": "",
        "access_token": "",
        "timezone": "Asia/Krasnoyarsk",
    },
    "copy": {
        "gate_eyebrow": "семейный маршрут",
        "gate_title": "Вход по ключу",
        "gate_hint": "Ключ есть в ссылке, которую тебе отправили",
        "gate_placeholder": "Ключ доступа",
        "gate_button": "Открыть",
        "gate_error": "Неверный ключ",
        "map_eyebrow": "семейный маршрут",
        "map_hint": "нажмите на точку — откроется день",
        "map_home_button": "← к карте",
        "note_label": "сообщение",
        "footer_updated": "Обновлено:",
        "footer_day": "{traveler} · {period}",
        "label_night": "ночёвка",
        "label_weather": "запас",
        "label_schedule": "расписание",
        "label_schedule_suffix": "пунктов",
        "label_journal": "из дороги",
        "label_note_block": "заметка",
        "label_photo_block": "фото",
        "pager_prev_day": "← день {n}",
        "pager_next_day": "день {n} →",
        "pager_prev_date": "← {date}",
        "pager_next_date": "{date} →",
        "day_eyebrow": "день {n} · {region}",
        "chapter_back": "Назад",
        "chapter_timeline_title": "Маршрут по дням",
        "chapter_cta": "Подробнее →",
        "day_back": "← К маршруту",
        "karl_chapter_home": "← к карте",
        "day_empty_placeholder": "Запись появится позже — пока только обложка дня.",
        "day_intro_label": "О дне",
        "day_schedule_label": "Расписание дня",
        "day_pager_prev": "← День {n}",
        "day_pager_next": "День {n} →",
    },
    "theme": {
        "theme_color": "#f7f0e1",
        "color_charcoal": "#23212c",
        "color_paper": "#f7f0e1",
        "color_paper_deep": "#ddd0b4",
        "color_surface": "#efe4cf",
        "color_surface_alt": "#e3d5bc",
        "color_surface_inset": "#f5edd9",
        "color_snow": "#ffffff",
        "color_pine": "#006434",
        "color_marigold": "#fcbd1c",
        "color_morning_sky": "#a6dfff",
        "color_ember": "#dd5000",
        "page_max_width": "640px",
        "font_family": '"Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif',
        "chapter_page_max_width": "40rem",
        "day_page_max_width": "40rem",
        "section_gap": "1rem",
        "card_radius": "1rem",
    },
    "custom_css": "",
}

THEME_CSS_MAP = {
    "theme_color": None,
    "color_charcoal": "--color-charcoal",
    "color_paper": "--color-paper",
    "color_paper_deep": "--color-paper-deep",
    "color_surface": "--color-surface",
    "color_surface_alt": "--color-surface-alt",
    "color_surface_inset": "--color-surface-inset",
    "color_snow": "--color-snow",
    "color_pine": "--color-pine",
    "color_marigold": "--color-marigold",
    "color_morning_sky": "--color-morning-sky",
    "color_ember": "--color-ember",
    "page_max_width": "--page-max-width",
    "chapter_page_max_width": "--chapter-page-max-width",
    "day_page_max_width": "--day-page-max-width",
    "section_gap": "--section-gap",
    "card_radius": "--card-radius",
    "font_family": "--font-neue-haas-unica",
}

ADMIN_SCHEMA: list[dict[str, Any]] = [
    {
        "id": "meta",
        "title": "Основное",
        "fields": [
            {"key": "traveler", "label": "Имя в заголовках", "type": "text"},
            {"key": "period", "label": "Период (подзаголовок)", "type": "text"},
            {"key": "subtitle", "label": "Подзаголовок маршрута", "type": "text"},
            {"key": "period_start", "label": "Начало (ISO)", "type": "text"},
            {"key": "period_end", "label": "Конец (ISO)", "type": "text"},
            {"key": "access_token", "label": "Ключ доступа (?k=)", "type": "text"},
            {"key": "timezone", "label": "Часовой пояс", "type": "text"},
        ],
    },
    {
        "id": "copy",
        "title": "Тексты на сайте",
        "hint": "В шаблонах {n}, {date}, {region}, {traveler}, {period} подставляются автоматически.",
        "fields": [
            {"key": "gate_eyebrow", "label": "Gate · eyebrow", "type": "text"},
            {"key": "gate_title", "label": "Gate · заголовок", "type": "text"},
            {"key": "gate_hint", "label": "Gate · подсказка", "type": "text"},
            {"key": "gate_placeholder", "label": "Gate · placeholder", "type": "text"},
            {"key": "gate_button", "label": "Gate · кнопка", "type": "text"},
            {"key": "gate_error", "label": "Gate · ошибка ключа", "type": "text"},
            {"key": "map_eyebrow", "label": "Главная · eyebrow", "type": "text"},
            {"key": "map_hint", "label": "Главная · подсказка", "type": "text"},
            {"key": "map_home_button", "label": "Кнопка «к карте»", "type": "text"},
            {"key": "note_label", "label": "Баннер · метка", "type": "text"},
            {"key": "footer_updated", "label": "Футер главной · префикс", "type": "text"},
            {"key": "footer_day", "label": "Футер дня", "type": "text"},
            {"key": "label_night", "label": "Метка «ночёвка»", "type": "text"},
            {"key": "label_weather", "label": "Метка «запас»", "type": "text"},
            {"key": "label_schedule", "label": "Метка «расписание»", "type": "text"},
            {"key": "label_schedule_suffix", "label": "Суффикс расписания", "type": "text"},
            {"key": "label_journal", "label": "Заголовок «из дороги»", "type": "text"},
            {"key": "label_note_block", "label": "Метка блока заметки", "type": "text"},
            {"key": "label_photo_block", "label": "Метка блока фото", "type": "text"},
            {"key": "pager_prev_day", "label": "Pager верх · назад", "type": "text"},
            {"key": "pager_next_day", "label": "Pager верх · вперёд", "type": "text"},
            {"key": "pager_prev_date", "label": "Pager низ · назад", "type": "text"},
            {"key": "pager_next_date", "label": "Pager низ · вперёд", "type": "text"},
            {"key": "day_eyebrow", "label": "Hero дня · eyebrow", "type": "text"},
            {"key": "chapter_back", "label": "Глава · назад к плиткам", "type": "text"},
            {"key": "chapter_timeline_title", "label": "Глава · заголовок таймлайна", "type": "text"},
            {"key": "chapter_cta", "label": "Глава · кнопка дня", "type": "text"},
            {"key": "day_back", "label": "День · назад к маршруту", "type": "text"},
            {"key": "day_intro_label", "label": "День · «О дне»", "type": "text"},
            {"key": "day_schedule_label", "label": "День · «Расписание»", "type": "text"},
            {"key": "day_pager_prev", "label": "День · pager назад", "type": "text"},
            {"key": "day_pager_next", "label": "День · pager вперёд", "type": "text"},
        ],
    },
    {
        "id": "theme",
        "title": "Цвета и ширина",
        "fields": [
            {"key": "theme_color", "label": "theme-color (браузер)", "type": "color"},
            {"key": "color_charcoal", "label": "Charcoal (текст)", "type": "color"},
            {"key": "color_paper", "label": "Paper (фон)", "type": "color"},
            {"key": "color_paper_deep", "label": "Paper deep", "type": "color"},
            {"key": "color_surface", "label": "Surface", "type": "color"},
            {"key": "color_surface_alt", "label": "Surface alt", "type": "color"},
            {"key": "color_surface_inset", "label": "Surface inset", "type": "color"},
            {"key": "color_snow", "label": "Snow (белый)", "type": "color"},
            {"key": "color_pine", "label": "Pine (акцент)", "type": "color"},
            {"key": "color_marigold", "label": "Marigold (маршрут)", "type": "color"},
            {"key": "color_morning_sky", "label": "Morning sky", "type": "color"},
            {"key": "color_ember", "label": "Ember (ошибки)", "type": "color"},
            {"key": "page_max_width", "label": "Макс. ширина страницы", "type": "text"},
            {"key": "chapter_page_max_width", "label": "Ширина страницы главы", "type": "text"},
            {"key": "day_page_max_width", "label": "Ширина страницы дня", "type": "text"},
            {"key": "section_gap", "label": "Отступ между секциями", "type": "text"},
            {"key": "card_radius", "label": "Скругление карточек", "type": "text"},
            {"key": "font_family", "label": "Шрифт (CSS font-family)", "type": "text"},
        ],
    },
    {
        "id": "custom_css",
        "title": "Свой CSS",
        "fields": [
            {"key": "custom_css", "label": "Дополнительные правила", "type": "textarea"},
        ],
    },
]


def deep_merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_legacy_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {k: data.get(k, v) for k, v in DEFAULTS["meta"].items() if k in data}


def load_site_settings() -> dict[str, Any]:
    stored: dict[str, Any] = {}
    if SETTINGS_PATH.exists():
        stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    merged = deep_merge(DEFAULTS, stored)
    merged["meta"] = deep_merge(DEFAULTS["meta"], deep_merge(load_legacy_config(), merged.get("meta", {})))
    if isinstance(merged.get("custom_css"), str):
        pass
    else:
        merged["custom_css"] = DEFAULTS["custom_css"]
    return merged


def save_site_settings(data: dict[str, Any]) -> dict[str, Any]:
    cleaned = sanitize_settings(data)
    SETTINGS_PATH.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    CONFIG_PATH.write_text(
        json.dumps(cleaned["meta"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return cleaned


def sanitize_settings(data: dict[str, Any]) -> dict[str, Any]:
    merged = deep_merge(DEFAULTS, data if isinstance(data, dict) else {})
    for key, css_var in THEME_CSS_MAP.items():
        if key == "theme_color" or css_var is None:
            continue
        value = merged["theme"].get(key, "")
        if key.startswith("color_") or key == "theme_color":
            if isinstance(value, str) and not HEX_COLOR.match(value.strip()):
                merged["theme"][key] = DEFAULTS["theme"][key]
    theme_color = merged["theme"].get("theme_color", DEFAULTS["theme"]["theme_color"])
    if isinstance(theme_color, str) and not HEX_COLOR.match(theme_color.strip()):
        merged["theme"]["theme_color"] = DEFAULTS["theme"]["theme_color"]
    merged["custom_css"] = str(merged.get("custom_css") or "")
    return merged


def format_copy(template: str, **kwargs: Any) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def render_theme_css(settings: dict[str, Any]) -> str:
    theme = settings.get("theme", DEFAULTS["theme"])
    lines = [
        "/* Generated by build_live_plan.py — edit in admin → Сайт */",
        ":root {",
    ]
    for key, css_var in THEME_CSS_MAP.items():
        if not css_var:
            continue
        value = theme.get(key, DEFAULTS["theme"].get(key, ""))
        if key == "font_family":
            lines.append(f"  {css_var}: {value};")
        else:
            lines.append(f"  {css_var}: {value};")
    lines.append("}")
    custom = (settings.get("custom_css") or "").strip()
    if custom:
        lines.extend(["", "/* Custom CSS */", custom])
    return "\n".join(lines) + "\n"


def admin_payload() -> dict[str, Any]:
    return {
        "settings": load_site_settings(),
        "schema": ADMIN_SCHEMA,
    }
