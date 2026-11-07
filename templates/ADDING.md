# Adding a dish

Copy `templates/recipe.template.json` to `recipes/<slug>.json` and fill it in. All data in English; the owner's language (Russian) goes only into `title_ru`, `aliases_ru`.

## Steps

1. **Collect the source.** For a YouTube Short: description, subtitles, top comments (`yt-dlp --skip-download --write-info-json --write-auto-subs --write-comments`). If the description points to a blog, take quantities from the blog's printable recipe.
2. **Fill the template** (rules below). Where the source gives no grams, estimate and say so in `note`.
3. **Photo.** Generate in Figma (file "Recipes") with the style prompt below, 1024×1024, save as `images/<slug>.png`.
4. **Build:** `python3 scripts/build.py` — it validates the rules and regenerates root `llms.txt` / `llms-full.txt`.
5. **Commit and push** to `main`. Pages redeploys automatically.

## Rules (enforced by build.py)

- `slug` = file name, lowercase kebab-case English.
- Every ingredient has `grams`, unless `"to_taste": true`. Pieces/spoons go to `qty` + `unit` *in addition* to grams.
- Every shopping item has `aisle` and `grams`, unless `"to_taste": true`.
  - `grams` = how much the recipe needs (net). If the store unit differs (whole pumpkin, can with liquid), describe it in `qty` and `note`.
- `aisle` ∈ `produce`, `meat_fish`, `dairy`, `bakery`, `grocery`, `frozen`, `spices`, `pantry`.
- `course` ∈ `appetizer`, `spread`, `salad`, `soup`, `main`, `side`, `breakfast`, `dessert`, `drink`, `sauce`, `baking`.
- `spice_level` ∈ `mild`, `medium`, `hot`.
- Steps carry the amounts inline ("add 300 g water"), so the cook never scrolls back.

## Photo style prompt

> Photorealistic food photography, top-down view. {Dish description: the finished dish exactly as served, with its toppings}. {1–2 props: a key raw ingredient or bread}. Light neutral linen background, soft natural daylight, no text.

## After cooking

When the owner reports how it went ("too spicy", "needed more salt"), adjust the recipe and add a dated line to `personal_notes`.
