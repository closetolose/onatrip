#!/usr/bin/env python3
"""Generate infographic PDF from пошаговый_гид_2026.md"""
import re
import html
from pathlib import Path
from playwright.sync_api import sync_playwright

from trip_parser import REGION, ROUTE, parse_md, transport_icon

ROOT = Path(__file__).parent
MD_PATH = ROOT / "пошаговый_гид_2026.md"
HTML_PATH = ROOT / "_guide_print.html"
PDF_PATH = ROOT / "пошаговый_гид_2026.pdf"


def esc(s: str) -> str:
    return html.escape(s).replace("**", "")


def bold_html(s: str) -> str:
    s = esc(s)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(s).replace("&amp;", "&"))


def render_step(step: dict) -> str:
    icon = transport_icon(step["action"] + " " + step["next"] + " " + step["place"])
    note = step["note"]
    alert = "alert" if any(w in note.lower() for w in ("не пропуст", "⏳", "залог", "без багажа", "04:30", "00:30", "05:15")) else ""
    transit = step["transit"]
    transit_html = ""
    if transit and transit != "—":
        transit_html = f'<span class="chip chip-transit">{esc(transit)}</span>'

    return f"""
    <div class="step {alert}">
      <div class="step-time">{esc(step['time'])}</div>
      <div class="step-line"><div class="dot">{icon}</div></div>
      <div class="step-body">
        <div class="step-place">{esc(step['place'])}</div>
        <div class="step-action">{esc(step['action'])}</div>
        <div class="step-meta">
          <span class="chip">{esc(step['duration'])}</span>
          {f'<span class="chip chip-next">→ {esc(step["next"])}</span>' if step['next'] and step['next'] != '—' else ''}
          {transit_html}
        </div>
        {f'<div class="step-note">{esc(note)}</div>' if note and note != '—' else ''}
      </div>
    </div>"""


def render_day(day: dict) -> str:
    r = REGION[day["region"]]
    steps_html = "".join(render_step(s) for s in day["steps"])
    totals_parts = [p.strip() for p in day["totals"].split("·")] if day["totals"] else []

    stats = ""
    for p in totals_parts:
        stats += f'<div class="stat-pill">{esc(p)}</div>'

    return f"""
    <section class="day-page" style="--region-color:{r['color']};--region-bg:{r['bg']};--region-accent:{r['accent']}">
      <header class="day-header">
        <div class="day-badge">День {day['num']}</div>
        <div class="day-title">
          <h2>{esc(day['date'])} <span class="weekday">{esc(day['weekday'])}</span></h2>
          <p class="city">{esc(day['city'])}</p>
        </div>
        <div class="region-tag">{r['name']}</div>
      </header>
      <div class="info-cards">
        <div class="info-card"><span class="label">Ночёвка</span><span class="value">{esc(day['night'])}</span></div>
        <div class="info-card"><span class="label">Запас / погода</span><span class="value">{esc(day['weather'])}</span></div>
      </div>
      <div class="timeline">{steps_html}</div>
      <footer class="day-footer">{stats}</footer>
    </section>"""


def render_html(data: dict) -> str:
    route_html = ""
    for i, (date, code, name, reg) in enumerate(ROUTE):
        r = REGION[reg]
        arrow = '<div class="route-arrow">→</div>' if i < len(ROUTE) - 1 else ""
        route_html += f"""
        <div class="route-node" style="--c:{r['accent']}">
          <div class="route-date">{date}</div>
          <div class="route-code">{code}</div>
          <div class="route-name">{name}</div>
        </div>{arrow}"""

    legend = "".join(
        f'<div class="legend-item"><span class="legend-dot" style="background:{r["accent"]}"></span>{r["name"]}</div>'
        for k, r in REGION.items() if k != "travel"
    )

    critical_html = "".join(
        f'<li><strong>{esc(t)}</strong> — {esc(d)}</li>' for t, d in data["critical"]
    )

    days_html = "".join(render_day(d) for d in data["days"])

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Пошаговый гид 28.07 — 25.08.2026</title>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
<style>
@page {{ size: A4; margin: 12mm 10mm; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Manrope', sans-serif; color: #111827; font-size: 9.5pt; line-height: 1.45; background: #fff; }}

.cover {{
  page-break-after: always;
  min-height: 260mm;
  padding: 18mm 14mm;
  background: linear-gradient(145deg, #0f172a 0%, #1e3a5f 40%, #7c2d12 100%);
  color: #fff;
  display: flex; flex-direction: column; justify-content: space-between;
}}
.cover h1 {{ font-size: 28pt; font-weight: 800; line-height: 1.15; letter-spacing: -0.02em; }}
.cover .subtitle {{ font-size: 12pt; opacity: 0.9; margin-top: 8px; }}
.cover .meta-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 24px;
}}
.cover .meta-box {{
  background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.2);
  border-radius: 12px; padding: 12px 14px; backdrop-filter: blur(4px);
}}
.cover .meta-box .lbl {{ font-size: 8pt; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.75; }}
.cover .meta-box .val {{ font-size: 11pt; font-weight: 700; margin-top: 4px; }}

.route-map {{
  display: flex; flex-wrap: wrap; align-items: center; justify-content: center;
  gap: 4px 2px; margin: 20px 0; padding: 16px;
  background: rgba(255,255,255,0.08); border-radius: 16px;
}}
.route-node {{
  text-align: center; min-width: 62px; padding: 8px 6px;
  background: rgba(255,255,255,0.95); color: #111; border-radius: 10px;
  border-top: 4px solid var(--c);
}}
.route-date {{ font-size: 7pt; color: #6b7280; font-weight: 600; }}
.route-code {{ font-family: 'JetBrains Mono', monospace; font-size: 11pt; font-weight: 700; color: var(--c); }}
.route-name {{ font-size: 7.5pt; font-weight: 600; margin-top: 2px; }}
.route-arrow {{ color: rgba(255,255,255,0.5); font-size: 14pt; font-weight: 700; }}

.legend {{ display: flex; flex-wrap: wrap; gap: 12px; }}
.legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 9pt; }}
.legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}

.overview {{
  page-break-after: always; padding: 8mm 2mm;
}}
.overview h2 {{ font-size: 16pt; margin-bottom: 12px; color: #0f172a; }}
.overview-grid {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
}}
.ov-card {{
  border-radius: 10px; padding: 10px; border-left: 4px solid var(--c);
  background: var(--bg); font-size: 8pt;
}}
.ov-card .d {{ font-weight: 800; font-size: 9pt; }}
.ov-card .c {{ color: #4b5563; margin-top: 2px; }}

.critical-page {{
  page-break-before: always; padding: 6mm 2mm;
}}
.critical-page h2 {{ font-size: 16pt; color: #b91c1c; margin-bottom: 12px; }}
.critical-page ul {{ list-style: none; }}
.critical-page li {{
  padding: 8px 10px; margin-bottom: 6px; border-radius: 8px;
  background: #fef2f2; border-left: 4px solid #ef4444; font-size: 8.5pt;
}}

.day-page {{
  page-break-before: always;
  padding: 4mm 2mm 8mm;
  border-top: 5px solid var(--region-accent);
}}
.day-header {{
  display: flex; align-items: flex-start; gap: 12px; margin-bottom: 10px;
}}
.day-badge {{
  background: var(--region-accent); color: #fff; font-weight: 800;
  padding: 8px 12px; border-radius: 10px; font-size: 10pt; white-space: nowrap;
}}
.day-title h2 {{ font-size: 15pt; font-weight: 800; color: var(--region-color); }}
.day-title .weekday {{ font-weight: 600; color: #6b7280; font-size: 11pt; }}
.day-title .city {{ font-size: 10pt; color: #374151; margin-top: 2px; }}
.region-tag {{
  margin-left: auto; background: var(--region-bg); color: var(--region-color);
  font-weight: 700; font-size: 8pt; padding: 6px 10px; border-radius: 999px;
}}

.info-cards {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }}
.info-card {{
  background: var(--region-bg); border-radius: 8px; padding: 8px 10px; font-size: 8pt;
}}
.info-card .label {{ display: block; font-weight: 700; color: var(--region-color); font-size: 7pt; text-transform: uppercase; letter-spacing: 0.05em; }}
.info-card .value {{ display: block; margin-top: 3px; color: #374151; }}

.timeline {{ position: relative; }}
.step {{
  display: grid; grid-template-columns: 52px 28px 1fr; gap: 6px;
  margin-bottom: 4px; align-items: start;
}}
.step.alert .step-body {{ background: #fff7ed; border-color: #fdba74; }}
.step-time {{
  font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 8.5pt;
  color: var(--region-color, #1f2937); text-align: right; padding-top: 6px;
}}
.step-line {{ display: flex; flex-direction: column; align-items: center; min-height: 100%; }}
.dot {{
  width: 26px; height: 26px; border-radius: 50%; background: #fff;
  border: 2px solid var(--region-accent, #6b7280);
  display: flex; align-items: center; justify-content: center; font-size: 11px;
  flex-shrink: 0;
}}
.step:not(:last-child) .step-line::after {{
  content: ''; flex: 1; width: 2px; background: #e5e7eb; margin-top: 2px; min-height: 8px;
}}
.step-body {{
  background: #fafafa; border: 1px solid #e5e7eb; border-radius: 8px;
  padding: 6px 9px; margin-bottom: 2px;
}}
.step-place {{ font-weight: 700; font-size: 8.5pt; color: #111827; }}
.step-action {{ font-size: 8.5pt; color: #374151; margin-top: 2px; }}
.step-meta {{ display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; }}
.chip {{
  font-size: 7pt; font-weight: 600; padding: 2px 6px; border-radius: 4px;
  background: #e5e7eb; color: #374151;
}}
.chip-next {{ background: #dbeafe; color: #1d4ed8; }}
.chip-transit {{ background: #fef3c7; color: #92400e; }}
.step-note {{ font-size: 7.5pt; color: #6b7280; margin-top: 4px; font-style: italic; }}

.day-footer {{
  display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; padding-top: 8px;
  border-top: 2px dashed #e5e7eb;
}}
.stat-pill {{
  font-size: 7.5pt; font-weight: 600; padding: 4px 8px; border-radius: 6px;
  background: var(--region-bg); color: var(--region-color);
}}

.footer-note {{
  page-break-before: always; text-align: center; color: #9ca3af; font-size: 8pt; padding: 20mm;
}}
</style>
</head>
<body>

<section class="cover">
  <div>
    <h1>Пошаговый гид<br>поездки 2026</h1>
    <p class="subtitle">Красноярск → Таиланд → Вьетнам → Китай → домой</p>
    <div class="meta-grid">
      <div class="meta-box"><div class="lbl">Период</div><div class="val">28.07 — 25.08.2026</div></div>
      <div class="meta-box"><div class="lbl">Дней в дороге</div><div class="val">29 дней</div></div>
      <div class="meta-box"><div class="lbl">Часовые пояса</div><div class="val">KJA/BKK +7 · Китай +8</div></div>
      <div class="meta-box"><div class="lbl">Формат</div><div class="val">1 человек · местное время</div></div>
    </div>
  </div>
  <div>
    <p style="font-size:9pt; opacity:0.8; margin-bottom:8px;">МАРШРУТ</p>
    <div class="route-map">{route_html}</div>
    <div class="legend">{legend}</div>
  </div>
</section>

<section class="overview">
  <h2>Обзор по дням</h2>
  <div class="overview-grid">
    {''.join(
        f'<div class="ov-card" style="--c:{REGION[d["region"]]["accent"]};--bg:{REGION[d["region"]]["bg"]}">'
        f'<div class="d">День {d["num"]} · {d["date"][:5]}</div>'
        f'<div class="c">{esc(d["city"])}</div></div>'
        for d in data["days"]
    )}
  </div>
</section>

{days_html}

<section class="critical-page">
  <h2>Критические точки</h2>
  <ul>{critical_html}</ul>
</section>

<div class="footer-note">
  Сгенерировано из пошаговый_гид_2026.md · Проверяй билеты и брони перед выездом
</div>
</body>
</html>"""


def main():
    md = MD_PATH.read_text(encoding="utf-8")
    data = parse_md(md)
    html_content = render_html(data)
    HTML_PATH.write_text(html_content, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(HTML_PATH.as_uri())
        page.wait_for_timeout(2000)
        page.pdf(
            path=str(PDF_PATH),
            format="A4",
            print_background=True,
            margin={"top": "10mm", "bottom": "10mm", "left": "8mm", "right": "8mm"},
        )
        browser.close()

    print(f"PDF: {PDF_PATH} ({PDF_PATH.stat().st_size // 1024} KB)")
    print(f"HTML: {HTML_PATH}")
    print(f"Days: {len(data['days'])}")


if __name__ == "__main__":
    main()
