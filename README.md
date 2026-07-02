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

### Важно: на Free Pages работает только для Public-репо

Если repo **private** — deploy через Actions висит 10 минут и падает с `Timeout reached`.  
Это не баг сайта, а ограничение GitHub.

**Решение:** Settings → General → **Change visibility → Public**  
(в `trip.json` нет PNR и бюджета; родным даёшь ссылку с ключом `?k=...`)

### Настройка (без Actions-deploy, надёжнее)

1. Запушь проект на GitHub.
2. **Settings → Pages**
3. **Source:** **Deploy from a branch** (не GitHub Actions!)
4. Branch: **main**, folder: **`/docs`**
5. Save → подожди 2–3 минуты.

Action `Build live plan` только собирает `docs/` и пушит в репо. Pages сам подхватывает из `/docs`.

6. Ссылка: `https://closetolose.github.io/onatrip/?k=trip2026live`

### Обновить заметку

Правишь `live_plan/status.json` → push → Action пересоберёт `docs/` → Pages обновится через 1–2 мин.

## Настройки

[live_plan/config.json](live_plan/config.json):

- `traveler` — имя в шапке
- `access_token` — ключ в URL (`?k=...`); пустая строка = без защиты
- `period`, `subtitle` — метаданные

### Свои фото и текст к дню

Файл [live_plan/day_media.json](live_plan/day_media.json):

```json
{
  "4": {
    "intro": "Остров Ко Лан — паром и пляжи",
    "photos": [
      {"url": "media/day-04/ko-lan.jpg", "caption": "Паром на Ко Лан"},
      "https://example.com/photo.jpg"
    ]
  }
}
```

Локальные фото клади в `live_plan/media/day-04/ko-lan.jpg` — при сборке копируются в `docs/media/`.  
Если фото не указаны — подставляется обложка по стране (Unsplash).

На главной каждый день открывается **в новой вкладке** с расписанием, фото и описанием.

### Админка (локально, с ноутбука)

Интерактивное редактирование фото: загрузка, перетаскивание, обрезка, подписи.

```bash
pip install -r requirements.txt
python admin_server.py
```

Открой: http://127.0.0.1:5050/

1. Выбери день слева
2. Загрузи фото или кликни по фото → обрежь и добавь подпись
3. Перетаскивай карточки для смены порядка
4. **Сохранить** → пишет `live_plan/day_media.json`
5. **Собрать сайт** → запускает `build_live_plan.py`
6. **Предпросмотр** → открывает страницу дня

Фото сохраняются в `live_plan/media/day-NN/`. После сборки — `git push` как обычно.

Админка работает **только локально** (127.0.0.1), в интернет не выходит.

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
