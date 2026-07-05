#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the public "postcards" travel site for GitHub Pages (docs/)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from live_plan.chapter_media import apply_chapter_overrides, load_chapter_media
from live_plan.chapters import build_chapters, current_chapter_id
from live_plan.day_pages import (
    MEDIA_SRC,
    blank_public_day,
    chapter_badges,
    enrich_chapter_days,
    intro_from_media,
    load_day_media,
    media_entry,
    missing_media_files,
    photos_from_media,
    verify_day_output,
)
from live_plan.layout import load_layout, render_layout_css
from live_plan.site_settings import format_copy, load_site_settings, render_theme_css
from trip_parser import REGION, parse_md

ROOT = Path(__file__).parent
LIVE_DIR = ROOT / "live_plan"
DOCS_DIR = ROOT / "docs"
ASSETS_SRC = LIVE_DIR / "assets"
GUIDE_PATH = ROOT / "пошаговый_гид_2026.md"

SECRET_MARKERS = ("PNR", "₽", "бюджет")


def verify_no_secrets(blob: str) -> None:
    """Abort the build if any secret marker leaked into the public JSON."""
    found = [marker for marker in SECRET_MARKERS if marker in blob]
    if found:
        raise SystemExit(f"Secret markers leaked into trip.json: {', '.join(found)}")


def build_trip(site: dict, parsed_days: list[dict], day_media: dict, chapter_media: dict) -> dict:
    chapters = build_chapters(parsed_days)
    chapters = [apply_chapter_overrides(chapter, chapter_media) for chapter in chapters]
    parsed_by_num = {day["num"]: day for day in parsed_days}
    chapter_by_id = {chapter["id"]: chapter for chapter in chapters}

    for chapter in chapters:
        enrich_chapter_days(chapter, parsed_by_num, day_media)

    meta = site["meta"]
    today_iso = datetime.now().date().isoformat()
    return {
        "meta": {
            "traveler": meta.get("traveler", "Путешественник"),
            "period": meta.get("period", ""),
            "subtitle": meta.get("subtitle", ""),
            "built_at": datetime.now().strftime("%d.%m.%Y %H:%M"),
        },
        "chapters": chapters,
        "current_chapter_id": current_chapter_id(chapters, today_iso),
        "_parsed_by_num": parsed_by_num,
        "_chapter_by_id": chapter_by_id,
    }


def render_index(trip: dict, theme_color: str) -> str:
    env = Environment(
        loader=FileSystemLoader(str(LIVE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("template.html")
    meta = trip["meta"]
    return template.render(
        chapters=trip["chapters"],
        traveler=meta["traveler"],
        period=meta["period"],
        subtitle=meta["subtitle"],
        built_at=meta["built_at"],
        theme_color=theme_color,
    )


def copy_context(site: dict) -> dict:
    return site.get("copy", {})


def render_chapter_pages(trip: dict, site: dict, theme_color: str) -> None:
    """Generate chapter overview pages linked from the main tiles."""
    env = Environment(
        loader=FileSystemLoader(str(LIVE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("chapter_template.html")
    chapters_dir = DOCS_DIR / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    meta = trip["meta"]

    for chapter in trip["chapters"]:
        if chapter["id"] == "departure":
            continue
        html = template.render(
            chapter=chapter,
            badges=chapter_badges(chapter),
            copy=copy_context(site),
            period=meta["period"],
            theme_color=theme_color,
        )
        (chapters_dir / f"{chapter['id']}.html").write_text(html, encoding="utf-8")


def render_day_pages(trip: dict, site: dict, theme_color: str, day_media: dict) -> None:
    """Generate day detail pages linked from chapter timelines."""
    env = Environment(
        loader=FileSystemLoader(str(LIVE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("day_template.html")
    days_dir = DOCS_DIR / "days"
    days_dir.mkdir(parents=True, exist_ok=True)

    parsed_by_num = trip["_parsed_by_num"]
    chapter_by_id = trip["_chapter_by_id"]
    copy = copy_context(site)
    meta = trip["meta"]
    day_nums = sorted(parsed_by_num)

    for day_num in day_nums:
        raw = parsed_by_num[day_num]
        entry = media_entry(day_num, day_media)
        public_day = blank_public_day(raw, entry)
        chapter = chapter_by_id[public_day["chapter_id"]]
        intro = intro_from_media(entry)
        verify_day_output({"day": public_day, "intro": intro})

        idx = day_nums.index(day_num)
        prev_day = parsed_by_num[day_nums[idx - 1]] if idx > 0 else None
        next_day = parsed_by_num[day_nums[idx + 1]] if idx + 1 < len(day_nums) else None

        html = template.render(
            day=public_day,
            chapter=chapter,
            region=REGION[public_day["region"]],
            photos=photos_from_media(day_num, public_day["region"], public_day["city"], entry),
            intro=intro,
            prev_day=prev_day,
            next_day=next_day,
            copy=copy,
            pager_prev=format_copy(copy.get("day_pager_prev", "← День {n}"), n=prev_day["num"]) if prev_day else "",
            pager_next=format_copy(copy.get("day_pager_next", "День {n} →"), n=next_day["num"]) if next_day else "",
            footer_day=format_copy(copy.get("footer_day", "{traveler} · {period}"), traveler=meta["traveler"], period=meta["period"]),
            traveler=meta["traveler"],
            period=meta["period"],
            theme_color=theme_color,
        )
        (days_dir / f"{day_num:02d}.html").write_text(html, encoding="utf-8")


def main() -> None:
    site = load_site_settings()
    theme_color = site.get("theme", {}).get("theme_color", "#f7f0e1")

    if not GUIDE_PATH.exists():
        raise SystemExit(f"Guide not found: {GUIDE_PATH}")

    parsed = parse_md(GUIDE_PATH.read_text(encoding="utf-8"))
    day_media = load_day_media()
    chapter_media = load_chapter_media()
    absent_media = missing_media_files(day_media)
    if absent_media:
        raise SystemExit(
            "Missing photo files referenced in live_plan/day_media.json:\n  "
            + "\n  ".join(absent_media)
            + "\nRestore them with: git checkout HEAD -- live_plan/media/"
        )
    trip = build_trip(site, parsed["days"], day_media, chapter_media)
    layout = load_layout()

    public_trip = {
        "meta": trip["meta"],
        "chapters": trip["chapters"],
        "current_chapter_id": trip["current_chapter_id"],
    }
    trip_blob = json.dumps(public_trip, ensure_ascii=False, indent=2)
    verify_no_secrets(trip_blob)

    docs_assets = DOCS_DIR / "assets"
    docs_assets.mkdir(parents=True, exist_ok=True)

    (DOCS_DIR / "trip.json").write_text(trip_blob + "\n", encoding="utf-8")
    (DOCS_DIR / "index.html").write_text(
        render_index(trip, theme_color), encoding="utf-8"
    )
    render_chapter_pages(trip, site, theme_color)
    render_day_pages(trip, site, theme_color, day_media)
    (DOCS_DIR / ".nojekyll").touch()

    shutil.copy2(ASSETS_SRC / "style.css", docs_assets / "style.css")
    shutil.copy2(ASSETS_SRC / "chapter.css", docs_assets / "chapter.css")
    shutil.copy2(ASSETS_SRC / "day.css", docs_assets / "day.css")
    shutil.copy2(ASSETS_SRC / "app.js", docs_assets / "app.js")
    (docs_assets / "theme.css").write_text(render_theme_css(site), encoding="utf-8")
    (docs_assets / "layout.css").write_text(render_layout_css(layout), encoding="utf-8")

    if MEDIA_SRC.exists():
        shutil.copytree(MEDIA_SRC, DOCS_DIR / "media", dirs_exist_ok=True)
    elif missing_media_files(day_media):
        raise SystemExit(f"Media folder not found: {MEDIA_SRC}")

    _clean_stale(docs_assets)

    print(f"Built: {DOCS_DIR / 'index.html'}")
    print(f"Built: {DOCS_DIR / 'chapters'} ({len(trip['chapters']) - 1} chapter pages)")
    print(f"Built: {DOCS_DIR / 'days'} ({len(trip['_parsed_by_num'])} day pages)")
    for chapter in trip["chapters"]:
        print(f"  {chapter['title']}: {chapter['day_count']} дн.")


def _clean_stale(docs_assets: Path) -> None:
    """Remove artefacts from previous site iterations."""
    podium_dir = docs_assets / "podium"
    if podium_dir.exists():
        shutil.rmtree(podium_dir)

    for stale_asset in ("map.js", "day.js", "plane.png"):
        path = docs_assets / stale_asset
        if path.exists():
            path.unlink()


if __name__ == "__main__":
    main()
