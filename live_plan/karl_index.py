# -*- coding: utf-8 -*-
"""Build Karl / Webflow globe pages — 1:1 karlgonsalves.com mirror, admin text only."""

from __future__ import annotations

import re
from html import escape

from pathlib import Path

from live_plan.chapter_vibes import KARL_ORIGINAL_TEXT, karl_colors, karl_texts

KARL_DIR = Path(__file__).resolve().parent / "karl_home"
TEMPLATE = KARL_DIR / "index.template.html"

_NAV_ORIGINAL = (
    ("HOME", "nav_home"),
    ("ABOUT", "nav_route"),
    ("WORK", "nav_main"),
    ("PLAY", "nav_play"),
    ("CONTACT", "nav_contact"),
)


def _strip_tracking(html: str) -> str:
    html = re.sub(
        r"<!--  Global site tag \(gtag\.js\).*?</script>\s*",
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(r"<script[^>]*>\s*window\.dataLayer.*?</script>\s*", "", html, flags=re.DOTALL)
    html = re.sub(r"<script>'undefined'=== typeof _trfq.*?</script>\s*", "", html, flags=re.DOTALL)
    html = re.sub(r"<script src='https://img1\.wsimg\.com/.*?</script>\s*", "", html, flags=re.DOTALL)
    html = re.sub(r"</body>\s*<script>.*?</html>", "</body>\n</html>", html, flags=re.DOTALL)
    blocks = re.findall(r"<style>.*?</style>", html, flags=re.DOTALL)
    if len(blocks) > 1:
        html = html.replace(blocks[1], "", 1)
    return html


def _prefix_assets(html: str, prefix: str) -> str:
    html = html.replace('href="css/', f'href="{prefix}css/')
    html = html.replace('href="images/', f'href="{prefix}images/')
    html = html.replace('src="images/', f'src="{prefix}images/')
    html = html.replace('src="js/', f'src="{prefix}js/')

    def _prefix_srcset(match: re.Match[str]) -> str:
        return 'srcset="' + match.group(1).replace("images/", f"{prefix}images/") + '"'

    html = re.sub(r'srcset="([^"]+)"', _prefix_srcset, html)
    return html


def _to_panel_html(text: str) -> str:
    return escape(text.strip()).replace("\n", "<br>")


def _apply_karl_nav(html: str, texts: dict[str, str]) -> str:
    for original, key in _NAV_ORIGINAL:
        label = escape(texts.get(key, KARL_ORIGINAL_TEXT[key]))
        html = html.replace(f">{original}</a>", f">{label}</a>")
    return html


def _globe_panel_angle(index: int, total: int) -> int:
    if total <= 1:
        return -180
    return round(-180 + (360 / (total - 1)) * index)


def _globe_chapter_days(chapter: dict) -> list[dict]:
    """Days shown on the Karl globe (Thailand includes trip day 1 / 28.07)."""
    days = list(chapter.get("days") or [])
    if chapter.get("id") == "thailand" and days and days[0].get("num", 0) > 1:
        days.insert(0, {"num": 1})
    return days


def _trip_day_for_panel(chapter: dict, chapter_index: int) -> int:
    """Map chapter label «День N» to trip day page number."""
    if chapter.get("id") == "thailand":
        return chapter_index
    days = chapter.get("days") or []
    if not days:
        return chapter_index
    return days[0]["num"] + chapter_index - 1


def _day_link_html(chapter: dict, chapter_index: int) -> str:
    trip_day = _trip_day_for_panel(chapter, chapter_index)
    href = f"../days/{trip_day:02d}.html"
    return f'<a href="{href}" class="karl-day-link text_a">День {chapter_index}</a>'


def _build_globe_pages_block(chapter: dict, intro_html: str) -> str:
    days = _globe_chapter_days(chapter)
    total = 1 + len(days)
    panels: list[str] = []
    intro_angle = _globe_panel_angle(0, total)
    panels.append(
        f'<div class="angle axis page_a page_panel" data-panel-index="0" '
        f'style="transform:rotateX({intro_angle}deg) rotateY(0deg) rotateZ(0deg);'
        f'transform-style:preserve-3d;-webkit-transform:rotateX({intro_angle}deg) '
        f'rotateY(0deg) rotateZ(0deg);-webkit-transform-style:preserve-3d;">'
        f'<div class="item pages"><div class="text_a">{intro_html}</div></div></div>'
    )
    for index, day in enumerate(days, start=1):
        angle = _globe_panel_angle(index, total)
        panels.append(
            f'<div class="angle axis page_day page_panel" data-panel-index="{index}" '
            f'style="transform:rotateX({angle}deg) rotateY(0deg) rotateZ(0deg);'
            f'transform-style:preserve-3d;-webkit-transform:rotateX({angle}deg) '
            f'rotateY(0deg) rotateZ(0deg);-webkit-transform-style:preserve-3d;">'
            f'<div class="item pages">{_day_link_html(chapter, index)}</div></div>'
        )
    inner = "\n          ".join(panels)
    return (
        '<div class="pages tilt axis">\n'
        '        <div class="pages rotate axis">\n'
        f"          {inner}\n"
        "        </div>\n"
        "      </div>"
    )


def _build_scroll_sections_block(chapter: dict) -> str:
    days = _globe_chapter_days(chapter)
    sections = ['<div id="Page_01_Home" class="page page_01"></div>']
    for index, _day in enumerate(days, start=1):
        page_num = index + 1
        sections.append(
            f'<div id="Page_Day_{index:02d}" class="page page_day page_{page_num:02d}"></div>'
        )
    return (
        '<div class="section section_behind">\n'
        f"    {'\n    '.join(sections)}\n"
        "  </div>"
    )


def _replace_globe_layers(html: str, pages_block: str) -> str:
    """Swap Karl template globe layers for chapter day panels (world under text)."""
    world_marker = '<div class="world axis"></div>'
    pages_marker = '<div class="pages tilt axis">'
    end_marker = '\n    </div>\n  </div>\n  <div class="section section_middle">'

    pages_i = html.find(pages_marker)
    if pages_i == -1:
        return html
    end_i = html.find(end_marker, pages_i)
    if end_i == -1:
        return html

    world_i = html.find(world_marker)
    if world_i != -1 and world_i < pages_i:
        start = world_i
    else:
        start = pages_i

    replacement = world_marker + "\n      " + pages_block
    return html[:start] + replacement + html[end_i:]


def _apply_chapter_day_globe(html: str, chapter: dict, texts: dict[str, str]) -> str:
    intro_html = _to_panel_html(texts.get("panel_a", KARL_ORIGINAL_TEXT["panel_a"]))
    pages_block = _build_globe_pages_block(chapter, intro_html)
    html = _replace_globe_layers(html, pages_block)
    scroll_block = _build_scroll_sections_block(chapter)
    html = re.sub(
        r'<div class="section section_behind">.*?</div>\s*</div>\s*<script src="https://d3e54v103j8qbb',
        scroll_block + '\n  <script src="https://d3e54v103j8qbb',
        html,
        count=1,
        flags=re.DOTALL,
    )
    return html


def _apply_karl_texts(html: str, texts: dict[str, str]) -> str:
    html = _apply_karl_nav(html, texts)
    html = html.replace(
        '<div class="text_a">Let&#x27;s<br>roll..</div>',
        f'<div class="text_a">{_to_panel_html(texts["panel_a"])}</div>',
    )
    html = html.replace(
        "<div class=\"text_a\">I&#x27;m Karl,</div>\n              "
        "<div class=\"text_b\">a motion designer.<br></div>",
        f"<div class=\"text_a\">{_to_panel_html(texts['panel_b_a'])}</div>\n              "
        f"<div class=\"text_b\">{_to_panel_html(texts['panel_b_b'])}<br></div>",
    )
    html = re.sub(
        r'(<div class="angle axis page_c">\s*<div class="item pages">\s*)'
        r'<div class="text_b">Visit my page on</div>'
        r'(<img[^>]+class="vimeo"[^>]*>)\s*'
        r'<div class="text_b">for my latest work\.</div>',
        (
            r"\1"
            f'<div class="text_b">{_to_panel_html(texts["panel_c_before"])}</div>'
            r"\2"
            f'<div class="text_b">{_to_panel_html(texts["panel_c_after"])}</div>'
        ),
        html,
        count=1,
        flags=re.DOTALL,
    )
    html = html.replace(
        "<div class=\"text_b\">I dabble in<br>web design too<br></div>\n              "
        "<div class=\"text_c\">.. sometimes.<br></div>",
        f"<div class=\"text_b\">{_to_panel_html(texts['panel_d_b'])}<br></div>\n              "
        f"<div class=\"text_c\">{_to_panel_html(texts['panel_d_c'])}<br></div>",
    )
    html = html.replace(
        "<div class=\"text_c\">Let&#x27;s talk!</div>\n              "
        "<div class=\"text_b\">phone or email<br></div>",
        f"<div class=\"text_c\">{_to_panel_html(texts['panel_e_c'])}</div>\n              "
        f"<div class=\"text_b\">{_to_panel_html(texts['panel_e_b'])}<br></div>",
    )
    return html


def _chapter_color_style(colors: dict[str, str], chapter_id: str) -> str:
    return f"""<style id="karl-chapter-colors">
  body.chapter-karl-{chapter_id} {{
    --karl-sky: {colors["sky"]};
    --karl-globe: {colors["globe"]};
    --karl-ink: {colors["ink"]};
    --karl-text-on-globe: {colors["text_on_globe"]};
    --karl-text-on-sky: {colors["text_on_sky"]};
  }}
  body.chapter-karl-{chapter_id}.body {{
    background-color: var(--karl-sky) !important;
  }}
  body.chapter-karl-{chapter_id} .world.axis,
  body.chapter-karl-{chapter_id} .axis.world {{
    background-color: var(--karl-globe) !important;
  }}
  body.chapter-karl-{chapter_id} .text_a,
  body.chapter-karl-{chapter_id} .text_b,
  body.chapter-karl-{chapter_id} .text_c {{
    color: var(--karl-text-on-globe);
  }}
  body.chapter-karl-{chapter_id} .menu_button {{
    color: var(--karl-ink);
  }}
  body.chapter-karl-{chapter_id} .menu_button:hover {{
    color: var(--karl-text-on-sky);
  }}
  body.chapter-karl .menu_button.button_01,
  body.chapter-karl .menu_button.button_02,
  body.chapter-karl .menu_button.button_03,
  body.chapter-karl .menu_button.button_04,
  body.chapter-karl .menu_button.button_05 {{
    display: none;
  }}
</style>"""


def _render_karl_html(
    *,
    asset_prefix: str,
    page_title: str | None,
    chapter_id: str | None,
    chapter: dict | None,
    media: dict | None,
    gate_html: str,
    extra_body: str,
) -> str:
    if not TEMPLATE.exists():
        raise FileNotFoundError(
            f"Missing {TEMPLATE}. Run: python scripts/mirror_karl_home.py"
        )

    html = TEMPLATE.read_text(encoding="utf-8")
    html = _strip_tracking(html)
    html = _prefix_assets(html, asset_prefix)

    colors = None
    if chapter_id:
        texts = karl_texts(chapter_id, media)
        colors = karl_colors(chapter_id, media)
        html = _apply_karl_nav(html, texts)
        if chapter and chapter.get("days"):
            html = _apply_chapter_day_globe(html, chapter, texts)
        else:
            html = _apply_karl_texts(html, texts)

    if page_title:
        html = html.replace("<title>Karl</title>", f"<title>{escape(page_title)}</title>")

    if chapter_id and colors is not None:
        html = html.replace(
            '<body overflow-x="hidden" class="body">',
            f'<body overflow-x="hidden" class="body chapter-karl chapter-karl-{chapter_id}" '
            f'data-chapter-id="{chapter_id}">',
        )
        html = html.replace(
            '<link href="../karl/css/karlgonsalves.webflow.css" rel="stylesheet" type="text/css">',
            '<link href="../karl/css/karlgonsalves.webflow.css" rel="stylesheet" type="text/css">\n  '
            '<link href="../assets/karl-chapter.css" rel="stylesheet" type="text/css">',
        )
        html = html.replace(
            "</head>",
            f'  <meta name="theme-color" content="{colors["sky"]}">\n  '
            f"{_chapter_color_style(colors, chapter_id)}\n</head>",
        )
        html = _inject_chapter_home_link(html)
    elif chapter_id and gate_html:
        html = html.replace(
            '<link href="../karl/css/karlgonsalves.webflow.css" rel="stylesheet" type="text/css">',
            '<link href="../karl/css/karlgonsalves.webflow.css" rel="stylesheet" type="text/css">\n  '
            '<link href="../assets/karl-chapter.css" rel="stylesheet" type="text/css">',
        )

    tail = f"{gate_html}\n{extra_body}".strip()
    if tail:
        html = html.replace("</body>", f"{tail}\n</body>")
    return html


def render_karl_chapter(
    *,
    chapter: dict,
    vibe: dict[str, str],
    page_title: str,
    gate_html: str,
    media: dict | None = None,
) -> str:
    del vibe  # copy comes from karl_texts(), not trip fields
    return _render_karl_html(
        asset_prefix="../karl/",
        page_title=page_title,
        chapter_id=chapter["id"],
        chapter=chapter,
        media=media,
        gate_html=gate_html,
        extra_body=(
            '  <script src="../assets/karl-chapter-days.js"></script>\n'
            '  <script src="../assets/app.js"></script>'
        ),
    )


def render_karl_mirror() -> str:
    """Pure karlgonsalves.com copy at docs/karl/index.html (no gate)."""
    return _render_karl_html(
        asset_prefix="",
        page_title=None,
        chapter_id=None,
        chapter=None,
        media=None,
        gate_html="",
        extra_body="",
    )


KARL_CHAPTER_IDS = frozenset({"thailand", "vietnam", "china"})

_HOME_LINK = (
    '<a href="../index.html" class="karl-chapter-home" aria-label="На главную с плитками">'
    "← Главная</a>"
)


def _inject_chapter_home_link(html: str) -> str:
    """Small corner control back to the tile map (index.html)."""
    return re.sub(
        r"(<body[^>]*chapter-karl[^>]*>)",
        rf"\1\n  {_HOME_LINK}",
        html,
        count=1,
    )
