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
DOCS_DIR = ROOT / "docs"
ASSETS_SRC = LIVE_DIR / "assets"

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
            "highlights": highlights,
            "main_event": main_highlight(day["steps"]),
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

    docs_assets = DOCS_DIR / "assets"
    docs_assets.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ASSETS_SRC, docs_assets, dirs_exist_ok=True)

    (DOCS_DIR / "trip.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (DOCS_DIR / "index.html").write_text(render_index(payload), encoding="utf-8")
    (DOCS_DIR / ".nojekyll").touch()

    print(f"Built: {DOCS_DIR / 'index.html'}")
    print(f"Built: {DOCS_DIR / 'trip.json'} ({len(payload['days'])} days)")
    if payload["meta"]["access_token"]:
        print(f"Share link: ...?k={payload['meta']['access_token']}")


if __name__ == "__main__":
    main()
