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

ROOT = Path(__file__).parent
LIVE_DIR = ROOT / "live_plan"
MEDIA_CONFIG_PATH = LIVE_DIR / "day_media.json"
MEDIA_SRC = LIVE_DIR / "media"
ADMIN_DIR = LIVE_DIR / "admin"
DOCS_DIR = ROOT / "docs"
MD_PATH = ROOT / "пошаговый_гид_2026.md"
CONFIG_PATH = LIVE_DIR / "config.json"

app = Flask(__name__, static_folder=str(ADMIN_DIR), static_url_path="")


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
        return payload.get("days", [])

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


def day_entry(media: dict, day_num: int) -> dict:
    return media.get(str(day_num), media.get(day_num, {})) or {}


def safe_filename(name: str) -> str:
    base = Path(name).name
    base = re.sub(r"[^\w.\-]+", "-", base, flags=re.UNICODE).strip(".-")
    return base or "photo.jpg"


@app.get("/")
def admin_index():
    return send_from_directory(ADMIN_DIR, "index.html")


@app.get("/api/days")
def api_days():
    return jsonify(load_days())


@app.get("/api/media")
def api_media_all():
    return jsonify(load_day_media())


@app.get("/api/media/<int:day_num>")
def api_media_day(day_num: int):
    media = load_day_media()
    entry = day_entry(media, day_num)
    return jsonify({
        "day": day_num,
        "intro": entry.get("intro", ""),
        "photos": entry.get("photos", []),
    })


@app.put("/api/media/<int:day_num>")
def api_save_day(day_num: int):
    payload = request.get_json(force=True)
    media = load_day_media()
    photos = payload.get("photos", [])
    cleaned_photos = []
    for item in photos:
        if isinstance(item, str):
            cleaned_photos.append({"url": item, "caption": ""})
        elif isinstance(item, dict) and item.get("url"):
            cleaned_photos.append({
                "url": item["url"],
                "caption": item.get("caption", ""),
            })

    media[str(day_num)] = {
        "intro": payload.get("intro", "").strip(),
        "photos": cleaned_photos,
    }
    save_day_media(media)
    return jsonify({"ok": True})


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
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    token = config.get("access_token", "")
    return jsonify({
        "access_token": token,
        "preview_base": "/preview",
    })


@app.get("/media/<path:filename>")
def serve_media(filename: str):
    return send_from_directory(MEDIA_SRC, filename)


@app.get("/preview/days/<path:filename>")
def preview_day(filename: str):
    return send_from_directory(DOCS_DIR / "days", filename)


@app.get("/preview/<path:filename>")
def preview_root(filename: str):
    return send_from_directory(DOCS_DIR, filename)


def main():
    MEDIA_SRC.mkdir(parents=True, exist_ok=True)
    print("Admin: http://127.0.0.1:5050/")
    app.run(host="127.0.0.1", port=5050, debug=False)


if __name__ == "__main__":
    main()
