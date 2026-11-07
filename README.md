# Рецепты

База рецептов для AI-агентов. Сайт: https://avkudryashov.github.io/recipes/ (вход для агентов — `llms.txt`).

## Структура

- `recipes/<slug>.json` — исходник рецепта (единственный источник правды).
- `images/<slug>.png` — фото готового блюда (генерируется в Figma, файл «Recipes»).
- `scripts/build.py` — собирает `_site/`: `llms.txt`, `llms-full.txt`, `index.json`, `recipes/<slug>.md|json`, `index.html`.
- `.github/workflows/pages.yml` — сборка и деплой на GitHub Pages при пуше в `main`.

## Добавить рецепт

1. Создать `recipes/<slug>.json` по образцу существующих (slug = имя файла, латиница через дефис).
2. Положить картинку в `images/<slug>.png`.
3. Проверить: `python3 scripts/build.py`.
4. Закоммитить и запушить в `main`.

## Поля рецепта

Обязательные: `slug`, `title`, `summary`, `course`, `tags`, `main_ingredients`, `servings`,
`time_min {prep, cook, total}`, `ingredients[] {name, grams?, qty?, unit?, note?, group?, optional?}`,
`shopping_list[] {item, qty, alt?}`, `steps[]`, `source {url, channel?, recipe_url?, note?}`.

Необязательные: `title_en`, `cuisine`, `diet`, `method`, `yield_g`, `nutrition`, `tips`, `storage`, `image`.
