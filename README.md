# Live plan

Минимальный лендинг для GitHub Pages.

## Сборка

```bash
pip install -r requirements.txt
python build_live_plan.py
```

Локально:

```bash
cd docs
python -m http.server 8080
```

Страница: http://localhost:8080/

## Настройка

Имя и подзаголовок — в [live_plan/site_settings.json](live_plan/site_settings.json).
