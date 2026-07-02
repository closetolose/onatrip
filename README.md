# Live plan — Share my trip

Read-only страница для родных: где ты сегодня, что завтра, короткая заметка.

## Быстрый старт

```bash
pip install -r requirements.txt
python build_live_plan.py
```

Открыть локально:

```bash
cd docs
python -m http.server 8080
```

Страница: http://localhost:8080/?k=trip2026live

## Обновить заметку в поездке

### С телефона (рекомендуется)

1. Открой репозиторий в **GitHub app** или браузере.
2. Файл [live_plan/status.json](live_plan/status.json) → **Edit**:

```json
{
  "note": "Прилетел в Дананг, всё ок",
  "note_updated": "2026-08-07T18:30:00+07:00",
  "status": "ok"
}
```

3. **Commit changes** — всё. Python на телефоне не нужен.

GitHub Action сам запустит `build_live_plan.py`, обновит `docs/` и запушит. Pages обновится через 1–2 минуты.

`status`: `ok` | `delay` | `issue` (жёлтый баннер для delay/issue).

### С компьютера

```bash
# отредактируй live_plan/status.json, затем:
git add live_plan/status.json
git commit -m "update live note"
git push
```

Action пересоберёт `docs/` автоматически. Локально `python build_live_plan.py` нужен только для предпросмотра.

## GitHub Pages

1. Создай репозиторий на GitHub и запушь проект.
2. Settings → Pages → Source: **Deploy from branch**.
3. Branch: **main**, folder: **/docs**.
4. Ссылка: `https://<user>.github.io/<repo>/?k=trip2026live`

Рекомендуется **private repo** — URL знают только те, кому скинул.

## Настройки

[live_plan/config.json](live_plan/config.json):

- `traveler` — имя в шапке
- `access_token` — ключ в URL (`?k=...`); пустая строка = без защиты
- `period`, `subtitle` — метаданные

## Источники данных

- [пошаговый_гид_2026.md](пошаговый_гид_2026.md) — расписание (без PNR и сумм в ₽)
- [live_plan/status.json](live_plan/status.json) — ручная заметка

## Структура

```
build_live_plan.py    # сборка
trip_parser.py        # парсер гида (общий с PDF)
live_plan/            # шаблон, конфиг, статус
docs/                 # GitHub Pages (генерируется)
```
