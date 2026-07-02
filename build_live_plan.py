#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build public live trip page for GitHub Pages (docs/)."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from trip_parser import REGION, ROUTE, parse_md, transport_icon

ROOT = Path(__file__).parent
MD_PATH = ROOT / "пошаговый_гид_2026.md"
LIVE_DIR = ROOT / "live_plan"
CONFIG_PATH = LIVE_DIR / "config.json"
STATUS_PATH = LIVE_DIR / "status.json"
MEDIA_CONFIG_PATH = LIVE_DIR / "day_media.json"
MEDIA_SRC = LIVE_DIR / "media"
DOCS_DIR = ROOT / "docs"
ASSETS_SRC = LIVE_DIR / "assets"

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

SANITIZE_PATTERNS = [
    (re.compile(r"PNR\s+\w+;?\s*", re.I), ""),
    (re.compile(r"~\d[\d\s–-]*\s*₽"), ""),
    (re.compile(r"\d[\d\s–-]*\s*₽"), ""),
    (re.compile(r"[^.;]*бюджет[^.;]*[.;]?\s*", re.I), ""),
    (re.compile(r"ориентир\s+\d+[^.;]*[.;]?\s*", re.I), ""),
    (re.compile(r"активности\s+\d[\d\s]*₽[^.;]*[.;]?\s*", re.I), ""),
    (re.compile(r"\s*;\s*;\s*"), "; "),
]


def sanitize_text(text: str) -> str:
    if not text or text == "—":
        return ""
    result = text.strip()
    for pattern, repl in SANITIZE_PATTERNS:
        result = pattern.sub(repl, result)
    result = re.sub(r"\s+", " ", result).strip(" ;.")
    return result


def step_blob(step: dict) -> str:
    return " ".join(
        step.get(k, "") for k in ("place", "action", "next", "note", "transit")
    ).lower()


def is_important_step(step: dict) -> bool:
    text = step_blob(step)
    if any(k in text for k in SKIP_KEYWORDS):
        if not any(k in text for k in ("рейс", "полёт", "полете", "аэропорт", "поезд", "паром", "прилёт", "прилет", "вылет", "иммиграц")):
            return False
    if any(k in text for k in IMPORTANT_KEYWORDS):
        return True
    icon = transport_icon(text)
    return icon in ("✈", "🚄", "⛴", "🚌") and "grab" not in text and "сонгтео" not in text


def date_to_iso(date_str: str) -> str:
    d, m, y = date_str.split(".")
    return f"{y}-{m}-{d}"


def pick_highlights(steps: list[dict], limit: int = 4) -> list[dict]:
    picked = []
    for step in steps:
        if not is_important_step(step):
            continue
        blob = step_blob(step)
        picked.append({
            "time": step["time"],
            "place": sanitize_text(step["place"]),
            "action": sanitize_text(step["action"]),
            "next": sanitize_text(step["next"]) if step["next"] != "—" else "",
            "icon": transport_icon(blob),
            "note": sanitize_text(step["note"]),
        })
        if len(picked) >= limit:
            break
    return picked


def sanitize_step(step: dict) -> dict | None:
    action = sanitize_text(step["action"]).lower()
    place = sanitize_text(step["place"]).lower()
    if action == "сон" or (action.startswith("сон") and "отель" not in place and "hotel" not in place):
        return None
    blob = step_blob(step)
    return {
        "time": step["time"],
        "place": sanitize_text(step["place"]),
        "action": sanitize_text(step["action"]),
        "next": sanitize_text(step["next"]) if step["next"] != "—" else "",
        "transit": sanitize_text(step["transit"]) if step["transit"] != "—" else "",
        "note": sanitize_text(step["note"]),
        "icon": transport_icon(blob),
    }


def build_day_steps(steps: list[dict]) -> list[dict]:
    result = []
    for step in steps:
        cleaned = sanitize_step(step)
        if cleaned and (cleaned["place"] or cleaned["action"]):
            result.append(cleaned)
    return result


def public_photo_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("media/"):
        return "../" + url
    return url


def resolve_photos(day_num: int, region: str, city: str, media_entry: dict) -> list[dict]:
    photos = []
    for item in media_entry.get("photos", []):
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
            "caption": media_entry.get("photo_caption") or f"{hero['caption']} · {city}",
        })
    return photos


def load_day_media() -> dict:
    if not MEDIA_CONFIG_PATH.exists():
        return {}
    return json.loads(MEDIA_CONFIG_PATH.read_text(encoding="utf-8"))


def main_highlight(steps: list[dict]) -> dict | None:
    highlights = pick_highlights(steps, limit=1)
    return highlights[0] if highlights else None


def build_trip_payload(config: dict, status: dict, data: dict) -> dict:
    built_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    days = []
    for day in data["days"]:
        highlights = pick_highlights(day["steps"])
        days.append({
            "num": day["num"],
            "date": day["date"],
            "date_iso": date_to_iso(day["date"]),
            "weekday": day["weekday"],
            "city": sanitize_text(day["city"]),
            "region": day["region"],
            "region_name": REGION[day["region"]]["name"],
            "night": sanitize_text(day["night"]),
            "weather": sanitize_text(day["weather"]),
            "totals": sanitize_text(day.get("totals", "")),
            "highlights": highlights,
            "main_event": main_highlight(day["steps"]),
            "page_url": f"days/{day['num']:02d}.html",
        })

    route = [
        {
            "date": date,
            "code": code,
            "name": name,
            "region": reg,
            "accent": REGION[reg]["accent"],
        }
        for date, code, name, reg in ROUTE
    ]

    return {
        "meta": {
            "traveler": config.get("traveler", "Путешественник"),
            "period": config.get("period", ""),
            "subtitle": config.get("subtitle", ""),
            "period_start": config.get("period_start", ""),
            "period_end": config.get("period_end", ""),
            "built_at": built_at,
            "access_token": config.get("access_token") or "",
        },
        "status": {
            "note": status.get("note", "").strip(),
            "note_updated": status.get("note_updated", ""),
            "status": status.get("status", "ok"),
        },
        "route": route,
        "days": days,
    }


def render_index(payload: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(LIVE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("template.html")
    return template.render(
        traveler=payload["meta"]["traveler"],
        period=payload["meta"]["period"],
        subtitle=payload["meta"]["subtitle"],
        built_at=payload["meta"]["built_at"],
        access_token=payload["meta"]["access_token"],
    )


def render_day_pages(payload: dict, raw_days: list[dict], day_media: dict) -> None:
    env = Environment(
        loader=FileSystemLoader(str(LIVE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("day_template.html")
    days_dir = DOCS_DIR / "days"
    days_dir.mkdir(parents=True, exist_ok=True)

    raw_by_num = {day["num"]: day for day in raw_days}
    token = payload["meta"]["access_token"]

    for day in payload["days"]:
        raw = raw_by_num[day["num"]]
        media_entry = day_media.get(str(day["num"]), day_media.get(day["num"], {}))
        region = REGION[day["region"]]
        html = template.render(
            day=day,
            region=region,
            steps=build_day_steps(raw["steps"]),
            photos=resolve_photos(day["num"], day["region"], day["city"], media_entry),
            intro=media_entry.get("intro", ""),
            traveler=payload["meta"]["traveler"],
            period=payload["meta"]["period"],
            access_token=token,
        )
        (days_dir / f"{day['num']:02d}.html").write_text(html, encoding="utf-8")


def verify_no_secrets(payload: dict) -> None:
    blob = json.dumps(payload, ensure_ascii=False)
    if re.search(r"PNR\s+\w+", blob, re.I):
        raise SystemExit("Sanitization failed: PNR found in output")
    if "₽" in blob:
        raise SystemExit("Sanitization failed: ruble amounts found in output")
    if "бюджет" in blob.lower():
        raise SystemExit("Sanitization failed: budget references found in output")


def main() -> None:
    if not MD_PATH.exists():
        raise SystemExit(f"Guide not found: {MD_PATH}")

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    data = parse_md(MD_PATH.read_text(encoding="utf-8"))
    payload = build_trip_payload(config, status, data)
    verify_no_secrets(payload)
    day_media = load_day_media()

    docs_assets = DOCS_DIR / "assets"
    docs_assets.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ASSETS_SRC, docs_assets, dirs_exist_ok=True)
    if MEDIA_SRC.exists():
        shutil.copytree(MEDIA_SRC, DOCS_DIR / "media", dirs_exist_ok=True)

    (DOCS_DIR / "trip.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (DOCS_DIR / "index.html").write_text(render_index(payload), encoding="utf-8")
    render_day_pages(payload, data["days"], day_media)
    (DOCS_DIR / ".nojekyll").touch()

    print(f"Built: {DOCS_DIR / 'index.html'}")
    print(f"Built: {DOCS_DIR / 'trip.json'} ({len(payload['days'])} days)")
    print(f"Built: {DOCS_DIR / 'days'} ({len(payload['days'])} day pages)")
    if payload["meta"]["access_token"]:
        print(f"Share link: ...?k={payload['meta']['access_token']}")


if __name__ == "__main__":
    main()
