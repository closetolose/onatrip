#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the public "postcards" travel site for GitHub Pages (docs/)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from live_plan.karl_index import KARL_CHAPTER_IDS, render_karl_chapter, render_karl_mirror
from live_plan.chapter_media import apply_chapter_overrides, load_chapter_media
from live_plan.chapter_vibes import chapter_vibe
from live_plan.chapters import build_chapters, current_chapter_id, assign_chapter
from live_plan.day_pages import (
    MEDIA_SRC,
    blank_public_day,
    chapter_badges,
    enrich_chapter_days,
    load_day_media,
    media_entry,
    missing_media_files,
    public_blocks,
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


def render_index(trip: dict, site: dict, theme_color: str) -> str:
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
        copy=copy_context(site),
        gate=gate_context(site),
    )


def copy_context(site: dict) -> dict:
    return site.get("copy", {})


def gate_context(site: dict) -> dict:
    return {"token": site.get("meta", {}).get("access_token", "")}


def render_chapter_pages(trip: dict, site: dict, theme_color: str) -> None:
    """Generate chapter overview pages linked from the main tiles."""
    env = Environment(
        loader=FileSystemLoader(str(LIVE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    diorama_template = env.get_template("chapter_template.html")
    chapters_dir = DOCS_DIR / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    meta = trip["meta"]
    copy = copy_context(site)
    gate = gate_context(site)
    chapter_media = load_chapter_media()

    for chapter in trip["chapters"]:
        vibe = chapter_vibe(chapter["id"], chapter_media)
        if chapter["id"] in KARL_CHAPTER_IDS:
            gate_html = env.get_template("gate_fragment.html").render(
                copy=copy,
                gate=gate,
            )
            html = render_karl_chapter(
                chapter=chapter,
                vibe=vibe,
                page_title=f"{chapter['title']} · {meta['period']}",
                gate_html=gate_html,
                media=chapter_media,
            )
        else:
            html = diorama_template.render(
                chapter=chapter,
                badges=chapter_badges(chapter),
                copy=copy,
                gate=gate,
                period=meta["period"],
                theme_color=vibe["sky"],
                vibe=vibe,
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
        chapter = chapter_by_id[assign_chapter(day_num)]
        if day_num == 1:
            chapter = chapter_by_id["thailand"]

        idx = day_nums.index(day_num)
        prev_day = parsed_by_num[day_nums[idx - 1]] if idx > 0 else None
        next_day = parsed_by_num[day_nums[idx + 1]] if idx + 1 < len(day_nums) else None

        region_key = raw["region"]
        if day_num == 1:
            region_key = "th"

        region_name = REGION[region_key]["name"]
        public_day = blank_public_day(raw, entry, region_name)

        blocks_out = public_blocks(day_num, public_day["region"], public_day["city"], entry)
        verify_day_output({"day": public_day, "blocks": blocks_out})

        html = template.render(
            day=public_day,
            chapter=chapter,
            region=REGION[region_key],
            blocks=blocks_out,
            prev_day=prev_day,
            next_day=next_day,
            copy=copy,
            gate=gate_context(site),
            pager_prev=format_copy(copy.get("day_pager_prev", "← День {n}"), n=prev_day["num"]) if prev_day else "",
            pager_next=format_copy(copy.get("day_pager_next", "День {n} →"), n=next_day["num"]) if next_day else "",
            footer_day=format_copy(copy.get("footer_day", "{traveler} · {period}"), traveler=meta["traveler"], period=meta["period"]),
            traveler=meta["traveler"],
            period=meta["period"],
            theme_color=REGION[region_key]["bg"],
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
        import sys
        print(
            "Warning: missing photo files referenced in live_plan/day_media.json:\n  "
            + "\n  ".join(absent_media)
            + "\nBuild continues; upload photos in admin or restore files under live_plan/media/.",
            file=sys.stderr,
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
        render_index(trip, site, theme_color), encoding="utf-8"
    )
    render_chapter_pages(trip, site, theme_color)
    render_day_pages(trip, site, theme_color, day_media)
    (DOCS_DIR / ".nojekyll").touch()

    shutil.copy2(ASSETS_SRC / "tokens.css", docs_assets / "tokens.css")
    shutil.copy2(ASSETS_SRC / "main.css", docs_assets / "main.css")
    shutil.copy2(ASSETS_SRC / "style.css", docs_assets / "style.css")
    shutil.copy2(ASSETS_SRC / "chapter.css", docs_assets / "chapter.css")
    shutil.copy2(ASSETS_SRC / "karl-chapter.css", docs_assets / "karl-chapter.css")
    shutil.copy2(ASSETS_SRC / "karl-chapter-days.js", docs_assets / "karl-chapter-days.js")
    shutil.copy2(ASSETS_SRC / "day.css", docs_assets / "day.css")
    shutil.copy2(ASSETS_SRC / "day.js", docs_assets / "day.js")
    shutil.copy2(ASSETS_SRC / "app.js", docs_assets / "app.js")
    (docs_assets / "theme.css").write_text(render_theme_css(site), encoding="utf-8")
    (docs_assets / "layout.css").write_text(render_layout_css(layout), encoding="utf-8")

    if MEDIA_SRC.exists():
        shutil.copytree(MEDIA_SRC, DOCS_DIR / "media", dirs_exist_ok=True)
    elif missing_media_files(day_media):
        raise SystemExit(f"Media folder not found: {MEDIA_SRC}")

    _clean_stale(docs_assets)
    _copy_karl_assets()
    (DOCS_DIR / "karl" / "index.html").write_text(render_karl_mirror(), encoding="utf-8")

    print(f"Built: {DOCS_DIR / 'index.html'}")
    print(f"Built: {DOCS_DIR / 'chapters'} ({len(trip['chapters'])} chapter pages)")
    print(f"Built: {DOCS_DIR / 'days'} ({len(trip['_parsed_by_num'])} day pages)")
    for chapter in trip["chapters"]:
        print(f"  {chapter['title']}: {chapter['day_count']} дн.")


def _copy_karl_assets() -> None:
    src = LIVE_DIR / "karl_home"
    dest = DOCS_DIR / "karl"
    for sub in ("css", "js", "images"):
        from_dir = src / sub
        to_dir = dest / sub
        if not from_dir.exists():
            raise FileNotFoundError(
                f"Missing {from_dir}. Run: python scripts/mirror_karl_home.py"
            )
        to_dir.mkdir(parents=True, exist_ok=True)
        for path in from_dir.iterdir():
            if path.is_file():
                shutil.copy2(path, to_dir / path.name)


def _clean_stale(docs_assets: Path) -> None:
    """Remove artefacts from previous site iterations."""
    podium_dir = docs_assets / "podium"
    if podium_dir.exists():
        shutil.rmtree(podium_dir)

    for stale_asset in ("map.js", "plane.png"):
        path = docs_assets / stale_asset
        if path.exists():
            path.unlink()


if __name__ == "__main__":
    main()
