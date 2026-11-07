# Recipes

Recipe knowledge base for AI agents. Site: https://avkudryashov.github.io/recipes/ (agent entry point: `llms.txt`).

All recipe data is in English; `title_ru` keeps the Russian dish name for search.

## Layout

- `recipes/<slug>.json` — recipe source (single source of truth).
- `images/<slug>.png` — finished-dish photo (generated in Figma, file "Recipes").
- `scripts/build.py` — builds `_site/`: `llms.txt`, `llms-full.txt`, `index.json`, `recipes/<slug>.md|json`, `index.html`.
- `.github/workflows/pages.yml` — build and deploy to GitHub Pages on push to `main`.

## Adding a recipe

1. Create `recipes/<slug>.json` following the existing ones (slug = file name, lowercase-kebab-case).
2. Put the photo at `images/<slug>.png`.
3. Check: `python3 scripts/build.py`.
4. Commit and push to `main`.

## Recipe fields

Required: `slug`, `title`, `summary`, `course`, `tags`, `main_ingredients`, `servings`,
`time_min {prep, cook, total}`, `ingredients[] {name, grams?, qty?, unit?, note?, group?, optional?}`,
`shopping_list[] {item, qty, alt?}`, `steps[]`, `source {url, channel?, recipe_url?, note?}`.

Optional: `title_ru`, `cuisine`, `diet`, `method`, `yield_g`, `nutrition`, `tips`, `storage`, `image`.
