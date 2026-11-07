#!/usr/bin/env python3
"""Build the AI-readable recipe site from recipes/*.json into _site/.

No external dependencies.
  python3 scripts/build.py          build _site/ and refresh root llms.txt / llms-full.txt
  python3 scripts/build.py --check  same, but fail if root llms files were stale (for CI)
Base URL comes from SITE_URL (defaults to this repo's GitHub Pages URL).
"""
import html
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "recipes"
IMAGES = ROOT / "images"
OUT = ROOT / "_site"
SITE_URL = os.environ.get("SITE_URL", "https://avkudryashov.github.io/recipes").rstrip("/")

REQUIRED = ["slug", "title", "title_ru", "summary", "course", "tags", "main_ingredients",
            "servings", "time_min", "ingredients", "shopping_list", "steps", "source"]
COURSES = {"appetizer", "spread", "salad", "soup", "main", "side", "breakfast",
           "dessert", "drink", "sauce", "baking"}
SPICE_LEVELS = {"mild", "medium", "hot"}
# Store order: how a shopper walks the aisles.
AISLES = {
    "produce": "Produce (vegetables, fruit, herbs)",
    "meat_fish": "Meat & fish",
    "dairy": "Dairy",
    "bakery": "Bakery",
    "grocery": "Grocery (cans, nuts, grains)",
    "frozen": "Frozen",
    "spices": "Spices",
    "pantry": "Pantry — check at home",
}


def validate(r, name):
    errs = [f"{name}: missing field '{k}'" for k in REQUIRED if k not in r]
    if errs:
        return errs
    if r["slug"] != name.removesuffix(".json"):
        errs.append(f"{name}: slug '{r['slug']}' does not match file name")
    bad = set(r["course"]) - COURSES
    if bad:
        errs.append(f"{name}: unknown course {sorted(bad)}; allowed {sorted(COURSES)}")
    if r.get("spice_level") and r["spice_level"] not in SPICE_LEVELS:
        errs.append(f"{name}: spice_level must be one of {sorted(SPICE_LEVELS)}")
    for i in r["ingredients"]:
        if "grams" not in i and not i.get("to_taste"):
            errs.append(f"{name}: ingredient '{i.get('name')}' needs 'grams' or 'to_taste': true")
    for s in r["shopping_list"]:
        if s.get("aisle") not in AISLES:
            errs.append(f"{name}: shopping item '{s.get('item')}' needs 'aisle' in {list(AISLES)}")
        if "grams" not in s and not s.get("to_taste"):
            errs.append(f"{name}: shopping item '{s.get('item')}' needs 'grams' or 'to_taste': true")
    return errs


def load_recipes():
    recipes, errors = [], []
    for path in sorted(SRC.glob("*.json")):
        try:
            r = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: invalid JSON: {e}")
            continue
        errors += validate(r, path.name)
        recipes.append(r)
    if errors:
        sys.exit("Recipe errors:\n" + "\n".join(errors))
    return recipes


def urls(r):
    base = f"{SITE_URL}/recipes/{r['slug']}"
    img = r.get("image")
    has_img = bool(img) and (ROOT / img).is_file()
    return {
        "md_url": f"{base}.md",
        "json_url": f"{base}.json",
        "image_url": f"{SITE_URL}/{img}" if has_img else None,
    }


def fmt_ing(i):
    if i.get("to_taste"):
        line = f"{i['name']} — to taste"
    else:
        line = f"{i['name']} — {i['grams']} g"
        if "qty" in i:
            qty = f"{i['qty']} {i.get('unit', '')}".strip()
            line += f" ({qty})"
    if i.get("note"):
        line += f"; {i['note']}"
    if i.get("optional"):
        line += " [optional]"
    return line


def fmt_shop(s):
    amount = "to taste" if s.get("to_taste") else f"{s['grams']} g"
    line = f"- [ ] {s['item']} — {amount}"
    if s.get("qty") and s["qty"] != "pantry":
        line += f" (buy: {s['qty']})"
    if s.get("note"):
        line += f"; {s['note']}"
    return line


def to_markdown(r):
    u = urls(r)
    t = r["time_min"]
    out = [f"# {r['title']}", "", f"*{r['title_ru']}*", ""]
    if r.get("aliases_ru"):
        out += [f"Also known as: {', '.join(r['aliases_ru'])}", ""]
    out += [r["summary"], ""]
    if u["image_url"]:
        out += [f"![{r['title']}]({u['image_url']})", ""]
    out += [
        f"- **Servings:** {r['servings']}" + (f" (yield ≈{r['yield_g']} g)" if r.get("yield_g") else ""),
        f"- **Time:** {t.get('total')} min (prep {t.get('prep')}, cook {t.get('cook')})",
        f"- **Course:** {', '.join(r['course'])}" + (f"; cuisine: {r['cuisine']}" if r.get("cuisine") else ""),
    ]
    for key, label in (("diet", "Diet"), ("method", "Method"), ("equipment", "Equipment")):
        if r.get(key):
            out.append(f"- **{label}:** {', '.join(r[key])}")
    if r.get("spice_level"):
        out.append(f"- **Spice level:** {r['spice_level']}")
    out.append(f"- **Tags:** {', '.join(r['tags'])}")
    n = r.get("nutrition")
    if n:
        extra = f", fiber {n['fiber_g']} g" if "fiber_g" in n else ""
        out.append(f"- **Nutrition ({n['basis']}):** {n['kcal']} kcal, protein {n['protein_g']} g, "
                   f"fat {n['fat_g']} g, carbs {n['carbs_g']} g{extra}" + (" — estimate" if n.get("estimated") else ""))

    out += ["", f"## Ingredients (for {r['servings']} servings)", ""]
    group = None
    for i in r["ingredients"]:
        if i.get("group") and i["group"] != group:
            if group is not None:
                out.append("")
            group = i["group"]
            out += [f"**{group}**", ""]
        out.append(f"- {fmt_ing(i)}")

    out += ["", f"## Shopping list (for {r['servings']} servings, grouped by store aisle)"]
    for aisle, label in AISLES.items():
        items = [s for s in r["shopping_list"] if s["aisle"] == aisle]
        if items:
            out += ["", f"**{label}**", ""] + [fmt_shop(s) for s in items]

    out += ["", "## Method", ""]
    out += [f"{k}. {s}" for k, s in enumerate(r["steps"], 1)]
    if r.get("tips"):
        out += ["", "## Tips", ""] + [f"- {x}" for x in r["tips"]]
    if r.get("storage"):
        out += ["", f"**Storage:** {r['storage']}"]
    src = r["source"]
    out += ["", "## Source", "", f"- Video: {src['url']}" + (f" ({src['channel']})" if src.get("channel") else "")]
    if src.get("recipe_url"):
        out.append(f"- Author's recipe: {src['recipe_url']}")
    if src.get("note"):
        out.append(f"- {src['note']}")
    out += ["", f"JSON: {u['json_url']}", ""]
    return "\n".join(out)


def index_entry(r):
    n = r.get("nutrition") or {}
    return {
        "slug": r["slug"],
        "title": r["title"],
        "title_ru": r["title_ru"],
        "aliases_ru": r.get("aliases_ru", []),
        "summary": r["summary"],
        "course": r["course"],
        "cuisine": r.get("cuisine"),
        "diet": r.get("diet", []),
        "method": r.get("method", []),
        "tags": r["tags"],
        "main_ingredients": r["main_ingredients"],
        "spice_level": r.get("spice_level"),
        "servings": r["servings"],
        "time_total_min": r["time_min"].get("total"),
        "kcal": n.get("kcal"),
        "kcal_basis": n.get("basis"),
        **urls(r),
    }


LLMS_HEADER = """# Recipes (knowledge base for AI agents)

> The owner's personal collection of tested recipes: gram quantities, store shopping lists grouped by aisle, nutrition estimates, and a photo of each finished dish. Data is in English; the owner speaks Russian (`title_ru`, `aliases_ru`). ALWAYS answer the owner in Russian.

## How to find a recipe

- Fetch {site}/index.json and match the request against `title_ru`, `aliases_ru`, `title`, `main_ingredients`, `tags`, `course`, `diet`, `method`.
- Then fetch the recipe's `md_url` (Markdown) or `json_url` (structured). Everything in one file: {site}/llms-full.txt
- Never invent quantities. If the recipe is not in the base, say so.

## Response rules (mandatory)

1. **Every quantity in grams.** Pieces / spoons / store packs only in parentheses after grams: «Баклажаны — 550 г (2 средних)». Spices with `to_taste` → «по вкусу».
2. **Scale** to the requested servings: grams × (requested / `servings`), round to 5 g (to 1 g under 20 g). When scaling UP, increase spices, ginger, chili and garlic more cautiously (≈75% of the factor, e.g. ×2 portions → ×1.75) and say so.
3. Show the photo (`image_url`) at the top when the interface can render images.

## Template A — at the store ("что купить", "список покупок")

Use `shopping_list`, grouped by `aisle` in this order: produce, meat_fish, dairy, bakery, grocery, frozen, spices, pantry. For several dishes, MERGE the lists and SUM grams of the same product, noting which dish needs what.

```
🛒 <title_ru> — <N> порций

Овощи и зелень
- [ ] Тыква — 450 г очищенной (купить 1 небольшую, 600–650 г)
- [ ] Имбирь — 7 г (кусочек 2 см)
Мясо и рыба
- [ ] Креветки — 225 г
Молочное
- [ ] Сливки 20 % — 200 г
Бакалея
- [ ] Тыквенные семечки — 20 г
Проверить дома
- Оливковое масло — 50 г
- Специи: карри (мягкое), мускатный орех — по вкусу
```

## Template B — cooking ("как готовить", "рецепт")

```
🍲 <title_ru> — <N> порций · <time> мин · <equipment>
Острота: <spice_level>

Ингредиенты
<group>
- <name> — <grams> г (<qty unit>)

Приготовление
1. <step with grams inline: «Налейте 300 г воды и 200 г сливок…»>
2. …

Советы: <1–3 most relevant tips>
```

## Template C — several dishes at once ("готовлю суп и салат")

First a combined timeline: what goes into the oven first and at what temperature, what to do while it bakes, what is finished last (things served hot, e.g. shrimp or steaks). Then each dish in Template B, with steps re-ordered to the timeline. Give one step at a time if the owner is cooking live.

## Recipes
"""


def write_if_changed(path, text):
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old != text:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main():
    check = "--check" in sys.argv
    recipes = load_recipes()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "recipes").mkdir(parents=True)
    if IMAGES.is_dir():
        shutil.copytree(IMAGES, OUT / "images")
    (OUT / ".nojekyll").write_text("")

    entries = []
    header = LLMS_HEADER.format(site=SITE_URL)
    full = [header.split("## Recipes")[0]]
    for r in recipes:
        md = to_markdown(r)
        (OUT / "recipes" / f"{r['slug']}.md").write_text(md, encoding="utf-8")
        (OUT / "recipes" / f"{r['slug']}.json").write_text(
            json.dumps({**r, **urls(r)}, ensure_ascii=False, indent=2), encoding="utf-8")
        entries.append(index_entry(r))
        full += ["---", "", md]

    (OUT / "index.json").write_text(json.dumps(
        {"site": SITE_URL, "count": len(entries), "recipes": entries},
        ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [header]
    for e in entries:
        lines.append(f"- [{e['title']}]({e['md_url']}) — {e['title_ru']} ({', '.join(e['aliases_ru'])}): "
                     f"{', '.join(e['course'])}; {', '.join(e['main_ingredients'])}; {e['time_total_min']} min")
    llms = "\n".join(lines) + "\n"
    llms_full = "\n".join(full)
    (OUT / "llms.txt").write_text(llms, encoding="utf-8")
    (OUT / "llms-full.txt").write_text(llms_full, encoding="utf-8")

    # Root copies so repo-based tools (GitMCP, GitHub search) see them too.
    stale = [name for name, text in (("llms.txt", llms), ("llms-full.txt", llms_full))
             if write_if_changed(ROOT / name, text)]

    items = "\n".join(
        f'<li><a href="recipes/{html.escape(e["slug"])}.md">{html.escape(e["title"])}</a> '
        f'(<a href="recipes/{html.escape(e["slug"])}.json">json</a>) — {html.escape(e["title_ru"])}</li>'
        for e in entries)
    (OUT / "index.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Recipes</title>
<link rel="alternate" type="text/plain" href="llms.txt">
<link rel="alternate" type="application/json" href="index.json">
</head><body>
<h1>Recipes</h1>
<p>Recipe knowledge base for AI agents. Start with <a href="llms.txt">llms.txt</a>,
full list in <a href="index.json">index.json</a>, everything in one file: <a href="llms-full.txt">llms-full.txt</a>.</p>
<ul>
{items}
</ul>
</body></html>
""", encoding="utf-8")
    print(f"Built {len(entries)} recipes → {OUT}")
    if check and stale:
        sys.exit(f"Root files were stale: {stale}. Run scripts/build.py and commit them.")


if __name__ == "__main__":
    main()
