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

## GitHub Pages

Сайт публикуется в ветку `gh-pages` через GitHub Actions.

В **Settings → Pages → Build and deployment** выберите:
- **Source:** Deploy from a branch
- **Branch:** `gh-pages` / `/ (root)`

Если деплой не обновляется, откройте **Actions → Deploy site → Run workflow**.
