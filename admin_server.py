#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local admin server for editing day photos and text."""
from __future__ import annotations

import json
import re
import subprocess
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from live_plan.blocks import clean_blocks, clean_hero, normalize_blocks
from live_plan.day_pages import default_hero
from live_plan.image_utils import optimize_image_file
from live_plan.chapter_media import (
    _sanitize_hex_color,
    chapter_entry,
    load_chapter_media,
    save_chapter_media,
    sanitize_chapter_media,
)
from live_plan.chapter_vibes import karl_defaults_for_admin
from live_plan.layout import admin_schema, load_layout, render_layout_css, save_layout
from live_plan.site_settings import admin_payload, load_site_settings, save_site_settings

from trip_parser import REGION

ROOT = Path(__file__).parent
LIVE_DIR = ROOT / "live_plan"
MEDIA_CONFIG_PATH = LIVE_DIR / "day_media.json"
MEDIA_SRC = LIVE_DIR / "media"
CHAPTER_MEDIA_SRC = LIVE_DIR / "media" / "chapters"
ADMIN_DIR = LIVE_DIR / "admin"
DOCS_DIR = ROOT / "docs"
MD_PATH = ROOT / "пошаговый_гид_2026.md"
STATUS_PATH = LIVE_DIR / "status.json"
CONFIG_PATH = LIVE_DIR / "config.json"

app = Flask(__name__, static_folder=str(ADMIN_DIR), static_url_path="")


@app.after_request
def admin_no_cache(response):
    if request.path.endswith((".js", ".html", ".css")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    return response


def load_day_media() -> dict:
    if not MEDIA_CONFIG_PATH.exists():
        return {}
    return json.loads(MEDIA_CONFIG_PATH.read_text(encoding="utf-8"))


def save_day_media(data: dict) -> None:
    MEDIA_CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_days() -> list[dict]:
    trip_path = DOCS_DIR / "trip.json"
    if trip_path.exists():
        payload = json.loads(trip_path.read_text(encoding="utf-8"))
        days: list[dict] = []
        for chapter in payload.get("chapters", []):
            for day in chapter.get("days", []):
                days.append({
                    "num": day["num"],
                    "date": day["date"],
                    "weekday": day.get("weekday", ""),
                    "city": day.get("city", ""),
                    "region": chapter.get("region", "travel"),
                    "chapter_id": chapter.get("id", ""),
                    "chapter_title": chapter.get("title", ""),
                })
        if days:
            return sorted(days, key=lambda item: item["num"])

    from trip_parser import parse_md

    data = parse_md(MD_PATH.read_text(encoding="utf-8"))
    return [
        {
            "num": day["num"],
            "date": day["date"],
            "weekday": day["weekday"],
            "city": day["city"],
            "region": day["region"],
        }
        for day in data["days"]
    ]


def load_chapters() -> list[dict]:
    trip_path = DOCS_DIR / "trip.json"
    if not trip_path.exists():
        return []
    payload = json.loads(trip_path.read_text(encoding="utf-8"))
    return [
        chapter for chapter in payload.get("chapters", [])
        if chapter.get("id") != "departure"
    ]


def get_raw_day(day_num: int) -> dict | None:
    from trip_parser import parse_md

    data = parse_md(MD_PATH.read_text(encoding="utf-8"))
    for day in data["days"]:
        if day["num"] == day_num:
            return day
    return None


def entry_hero(entry: dict) -> dict[str, str] | None:
    """Saved hero text, or None when nothing was stored yet."""
    if "hero" not in entry:
        return None
    cleaned = clean_hero(entry.get("hero"))
    if not any(cleaned.values()):
        return None
    return cleaned


def admin_hero_for_entry(entry: dict, guide: dict, region_name: str) -> dict[str, str]:
    """Hero fields for the admin form."""
    saved = entry_hero(entry)
    if saved is not None:
        return saved
    return default_hero(guide, region_name)


def day_media_response(day_num: int) -> dict:
    media = load_day_media()
    entry = day_entry(media, day_num)
    guide = guide_day_for(day_num)
    region_name = region_display_name(guide.get("region", "travel"), day_num)
    return {
        "day": day_num,
        "hero": admin_hero_for_entry(entry, guide, region_name),
        "defaults": default_hero(guide, region_name),
        "blocks": normalize_blocks(entry),
    }


def guide_day_for(day_num: int) -> dict:
    for day in load_days():
        if day["num"] == day_num:
            return {
                "num": day["num"],
                "date": day.get("date", ""),
                "weekday": day.get("weekday", ""),
                "city": day.get("city", ""),
                "region": day.get("region", "travel"),
            }
    raw = get_raw_day(day_num)
    if raw:
        return raw
    return {"num": day_num, "date": "", "weekday": "", "city": "", "region": "travel"}


def region_display_name(region_key: str, day_num: int) -> str:
    if day_num == 1:
        region_key = "th"
    return REGION.get(region_key, REGION["travel"])["name"]


def day_entry(media: dict, day_num: int) -> dict:
    return media.get(str(day_num), media.get(day_num, {})) or {}


def write_day_entry(media: dict, day_num: int, entry: dict) -> None:
    media[str(day_num)] = entry
    save_day_media(media)


def save_day_entry(media: dict, day_num: int, hero: dict, blocks: list) -> dict:
    entry = {
        "hero": clean_hero(hero),
        "blocks": clean_blocks(blocks),
    }
    write_day_entry(media, day_num, entry)
    return entry


def safe_filename(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\-]+", "-", base, flags=re.UNICODE).strip(".-")
    return base or "photo.jpg"


@app.get("/")
def admin_index():
    return send_from_directory(ADMIN_DIR, "index.html")


@app.get("/api/chapters")
def api_chapters():
    media = load_chapter_media()
    chapters = load_chapters()
    return jsonify([
        {
            **chapter,
            "override": chapter_entry(chapter["id"], media),
        }
        for chapter in chapters
    ])


@app.get("/api/chapters/<chapter_id>")
def api_chapter_get(chapter_id: str):
    chapters = {chapter["id"]: chapter for chapter in load_chapters()}
    chapter = chapters.get(chapter_id)
    if not chapter:
        return jsonify({"error": "chapter not found"}), 404
    return jsonify({
        "chapter": chapter,
        "override": chapter_entry(chapter_id, load_chapter_media()),
        "karl_defaults": karl_defaults_for_admin(chapter_id),
    })


@app.put("/api/chapters/<chapter_id>")
def api_chapter_put(chapter_id: str):
    payload = request.get_json(force=True)
    media = load_chapter_media()
    entry = {
        "title": str(payload.get("title", "")).strip(),
        "description": str(payload.get("description", "")).strip(),
        "hero_image": str(payload.get("hero_image", "")).strip(),
        "page_bg": _sanitize_hex_color(payload.get("page_bg", "")),
        "badges": [str(item).strip() for item in payload.get("badges", []) if str(item).strip()],
        "highlights": [str(item).strip() for item in payload.get("highlights", []) if str(item).strip()],
        "day_overrides": payload.get("day_overrides") or {},
        "karl": payload.get("karl") or {},
    }
    cleaned = sanitize_chapter_media({**media, chapter_id: entry})
    save_chapter_media(cleaned)
    return jsonify({"ok": True, "override": cleaned.get(chapter_id, {})})


@app.post("/api/chapters/<chapter_id>/upload-hero")
def api_chapter_upload_hero(chapter_id: str):
    if "file" not in request.files:
        return jsonify({"error": "file required"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "empty filename"}), 400
    ext = Path(safe_filename(file.filename)).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return jsonify({"error": "unsupported file type"}), 400
    chapter_dir = CHAPTER_MEDIA_SRC / chapter_id
    chapter_dir.mkdir(parents=True, exist_ok=True)
    filename = f"hero-{uuid.uuid4().hex[:10]}{ext}"
    target = chapter_dir / filename
    file.save(target)
    url = f"media/chapters/{chapter_id}/{filename}"
    return jsonify({"url": url})


def write_layout_css(layout: dict | None = None) -> None:
    css = render_layout_css(layout or load_layout())
    target = DOCS_DIR / "assets" / "layout.css"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(css, encoding="utf-8")


@app.get("/api/layout")
def api_layout_get():
    return jsonify({
        "layout": load_layout(),
        "schema": admin_schema(),
    })


@app.put("/api/layout")
def api_layout_put():
    payload = request.get_json(force=True)
    saved = save_layout(payload.get("layout", payload))
    write_layout_css(saved)
    return jsonify({"ok": True, "layout": saved})


@app.post("/api/layout/css")
def api_layout_css():
    payload = request.get_json(force=True)
    from live_plan.layout import render_layout_css, sanitize_layout

    layout = sanitize_layout(payload.get("layout", payload))
    return jsonify({"css": render_layout_css(layout)})


@app.post("/api/layout/reset")
def api_layout_reset():
    from live_plan.layout import DEFAULT_LAYOUT, save_layout

    saved = save_layout(DEFAULT_LAYOUT)
    write_layout_css(saved)
    return jsonify({"ok": True, "layout": saved})


@app.get("/preview/chapters/<path:filename>")
def preview_chapter(filename: str):
    return send_from_directory(DOCS_DIR / "chapters", filename)


@app.get("/api/health")
def api_health():
    days = load_days()
    chapters = load_chapters()
    trip_exists = (DOCS_DIR / "trip.json").exists()
    return jsonify({
        "ok": True,
        "days_count": len(days),
        "chapters_count": len(chapters),
        "trip_built": trip_exists,
        "preview_ready": (DOCS_DIR / "chapters" / "thailand.html").exists(),
    })


@app.get("/api/days")
def api_days():
    return jsonify(load_days())


@app.get("/api/version")
def api_version():
    return jsonify({"version": 3, "features": ["hero", "blocks"]})


@app.get("/api/media")
def api_media_all():
    return jsonify(load_day_media())


@app.get("/api/media/<int:day_num>")
def api_media_day(day_num: int):
    return jsonify(day_media_response(day_num))


@app.put("/api/media/<int:day_num>")
@app.post("/api/media/<int:day_num>/save")
def api_save_day(day_num: int):
    payload = request.get_json(force=True)
    media = load_day_media()
    hero = payload.get("hero", {})
    blocks = payload.get("blocks", [])
    saved_entry = save_day_entry(media, day_num, hero, blocks)
    response = day_media_response(day_num)
    response["ok"] = True
    response["hero_written"] = saved_entry.get("hero", clean_hero(hero))
    response["blocks_written"] = saved_entry.get("blocks", [])
    return jsonify(response)


@app.post("/api/media/<int:day_num>/reset-schedule")
def api_reset_schedule(day_num: int):
    media = load_day_media()
    entry = day_entry(media, day_num)
    entry.pop("steps", None)
    entry.pop("meta", None)
    if entry.get("blocks") is not None:
        write_day_entry(media, day_num, entry)
    elif str(day_num) in media:
        media.pop(str(day_num), None)
        save_day_media(media)
    return jsonify(day_media_response(day_num))


@app.post("/api/upload/<int:day_num>")
def api_upload(day_num: int):
    if "file" not in request.files:
        return jsonify({"error": "file required"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "empty filename"}), 400

    ext = Path(safe_filename(file.filename)).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return jsonify({"error": "unsupported file type"}), 400

    day_dir = MEDIA_SRC / f"day-{day_num:02d}"
    day_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex[:10]}{ext}"
    target = day_dir / filename
    file.save(target)
    optimize_image_file(target)

    url = f"media/day-{day_num:02d}/{filename}"
    return jsonify({"url": url, "caption": ""})


@app.post("/api/crop/<int:day_num>")
def api_crop(day_num: int):
    if "file" not in request.files:
        return jsonify({"error": "file required"}), 400

    source_url = request.form.get("source_url", "")
    if not source_url.startswith(f"media/day-{day_num:02d}/"):
        return jsonify({"error": "invalid source"}), 400

    file = request.files["file"]
    ext = Path(source_url).suffix.lower() or ".jpg"
    day_dir = MEDIA_SRC / f"day-{day_num:02d}"
    day_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex[:10]}-crop{ext}"
    target = day_dir / filename
    file.save(target)
    optimize_image_file(target)

    return jsonify({"url": f"media/day-{day_num:02d}/{filename}"})


@app.post("/api/build")
def api_build():
    result = subprocess.run(
        ["python", str(ROOT / "build_live_plan.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return jsonify({
        "ok": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "code": result.returncode,
    })


@app.get("/api/config")
def api_config():
    site = load_site_settings()
    token = site["meta"].get("access_token", "")
    return jsonify({
        "access_token": token,
        "preview_base": "/preview",
    })


@app.get("/api/site-settings")
def api_site_settings_get():
    return jsonify(admin_payload())


@app.put("/api/site-settings")
def api_site_settings_put():
    payload = request.get_json(force=True)
    saved = save_site_settings(payload)
    return jsonify({"ok": True, "settings": saved})


@app.get("/api/status")
def api_status_get():
    if not STATUS_PATH.exists():
        return jsonify({"note": "", "note_updated": "", "status": "ok"})
    return jsonify(json.loads(STATUS_PATH.read_text(encoding="utf-8")))


@app.put("/api/status")
def api_status_put():
    payload = request.get_json(force=True)
    data = {
        "note": str(payload.get("note", "")).strip(),
        "note_updated": str(payload.get("note_updated", "")).strip(),
        "status": payload.get("status", "ok") if payload.get("status") in {"ok", "delay", "issue"} else "ok",
    }
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return jsonify({"ok": True, **data})


@app.post("/api/site-settings/reset")
def api_site_settings_reset():
    from live_plan.site_settings import DEFAULTS, save_site_settings

    saved = save_site_settings(DEFAULTS)
    return jsonify({"ok": True, "settings": saved})


@app.get("/media/<path:filename>")
def serve_media(filename: str):
    return send_from_directory(MEDIA_SRC, filename)


@app.get("/preview/days/<path:filename>")
def preview_day(filename: str):
    return send_from_directory(DOCS_DIR / "days", filename)


@app.get("/preview/<path:filename>")
def preview_root(filename: str):
    return send_from_directory(DOCS_DIR, filename)


def ensure_site_built() -> None:
    """Build docs/ when missing so the admin UI has data and previews."""
    trip_path = DOCS_DIR / "trip.json"
    needs_build = not trip_path.exists()
    if trip_path.exists():
        try:
            payload = json.loads(trip_path.read_text(encoding="utf-8"))
            day_count = sum(len(ch.get("days", [])) for ch in payload.get("chapters", []))
            needs_build = day_count == 0
        except json.JSONDecodeError:
            needs_build = True
    if not needs_build:
        return
    print("Building site (docs/) for admin…")
    result = subprocess.run(
        ["python", str(ROOT / "build_live_plan.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        print("Build failed:")
        print(result.stderr or result.stdout)
    else:
        print(result.stdout.strip())


def main():
    MEDIA_SRC.mkdir(parents=True, exist_ok=True)
    CHAPTER_MEDIA_SRC.mkdir(parents=True, exist_ok=True)
    ensure_site_built()
    days_count = len(load_days())
    print(f"Admin: http://127.0.0.1:5050/  ({days_count} days loaded)")
    print("Open this URL in the browser — do not open index.html as a file.")
    app.run(host="127.0.0.1", port=5050, debug=False)


if __name__ == "__main__":
    main()
