#!/usr/bin/env python3
"""Build the AI-readable recipe site from recipes/*.json into _site/.

No external dependencies. Run: python3 scripts/build.py
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

REQUIRED = ["slug", "title", "summary", "course", "tags", "main_ingredients",
            "servings", "time_min", "ingredients", "shopping_list", "steps", "source"]


def load_recipes():
    recipes, errors = [], []
    for path in sorted(SRC.glob("*.json")):
        try:
            r = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{path.name}: invalid JSON: {e}")
            continue
        missing = [k for k in REQUIRED if k not in r]
        if missing:
            errors.append(f"{path.name}: missing fields {missing}")
        if r.get("slug") != path.stem:
            errors.append(f"{path.name}: slug '{r.get('slug')}' does not match file name")
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
    parts = []
    if "qty" in i:
        parts.append(f"{i['qty']} {i.get('unit', '')}".strip())
    if "grams" in i:
        g = f"{i['grams']} g"
        parts.append(f"({g})" if parts else g)
    amount = " ".join(parts)
    line = f"{i['name']} — {amount}" if amount else i["name"]
    if i.get("note"):
        line += f"; {i['note']}"
    if i.get("optional"):
        line += " (optional)"
    return line


def to_markdown(r):
    u = urls(r)
    t = r["time_min"]
    out = [f"# {r['title']}", ""]
    if r.get("title_ru"):
        out += [f"*{r['title_ru']}*", ""]
    out += [r["summary"], ""]
    if u["image_url"]:
        out += [f"![{r['title']}]({u['image_url']})", ""]
    out += [
        f"- **Servings:** {r['servings']}" + (f" (yield ≈{r['yield_g']} g)" if r.get("yield_g") else ""),
        f"- **Time:** {t.get('total')} min (prep {t.get('prep')}, cook {t.get('cook')})",
        f"- **Course:** {', '.join(r['course'])}" + (f"; cuisine: {r['cuisine']}" if r.get("cuisine") else ""),
    ]
    if r.get("diet"):
        out.append(f"- **Diet:** {', '.join(r['diet'])}")
    if r.get("method"):
        out.append(f"- **Method:** {', '.join(r['method'])}")
    out.append(f"- **Tags:** {', '.join(r['tags'])}")
    n = r.get("nutrition")
    if n:
        extra = f", fiber {n['fiber_g']} g" if "fiber_g" in n else ""
        out.append(f"- **Nutrition ({n['basis']}):** {n['kcal']} kcal, protein {n['protein_g']} g, "
                   f"fat {n['fat_g']} g, carbs {n['carbs_g']} g{extra}" + (" — estimate" if n.get("estimated") else ""))
    out += ["", f"## Ingredients (for {r['servings']} servings)"]
    group = None
    for i in r["ingredients"]:
        if i.get("group") and i["group"] != group:
            group = i["group"]
            out += ["", f"**{group}**"]
        if group is None and out[-1].startswith("##"):
            out.append("")
        out.append(f"- {fmt_ing(i)}")
    out += ["", "## Shopping list", ""]
    for s in r["shopping_list"]:
        line = f"- [ ] {s['item']} — {s['qty']}"
        if s.get("alt"):
            line += f" (or: {s['alt']})"
        out.append(line)
    out += ["", "## Method", ""]
    out += [f"{n}. {s}" for n, s in enumerate(r["steps"], 1)]
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
        "title_ru": r.get("title_ru"),
        "summary": r["summary"],
        "course": r["course"],
        "cuisine": r.get("cuisine"),
        "diet": r.get("diet", []),
        "method": r.get("method", []),
        "tags": r["tags"],
        "main_ingredients": r["main_ingredients"],
        "servings": r["servings"],
        "time_total_min": r["time_min"].get("total"),
        "kcal": n.get("kcal"),
        "kcal_basis": n.get("basis"),
        **urls(r),
    }


LLMS_HEADER = """# Recipes (knowledge base for AI agents)

> A personal collection of tested recipes with gram quantities, shopping lists, nutrition estimates and a photo of the finished dish. The owner speaks Russian: `title_ru` holds the Russian dish name — answer the user in Russian unless asked otherwise.

How to use:
- Find a recipe: fetch {site}/index.json (every recipe with tags, main ingredients, time and kcal) and filter by `tags`, `main_ingredients`, `course`, `diet`, `method`, `title`, `title_ru`.
- Everything in one file: {site}/llms-full.txt
- A single recipe: `md_url` (Markdown) or `json_url` (structured data).
- User is at the store → return the "Shopping list" (`shopping_list`). User is cooking → return "Ingredients" and "Method".
- Scaling: quantities are for `servings` servings; scale proportionally, be more conservative with spices.
- Finished-dish photo: `image_url` (PNG), may be shown to the user.

## Recipes
"""


def main():
    recipes = load_recipes()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "recipes").mkdir(parents=True)
    if IMAGES.is_dir():
        shutil.copytree(IMAGES, OUT / "images")
    (OUT / ".nojekyll").write_text("")

    entries = []
    full = [LLMS_HEADER.format(site=SITE_URL).split("## Recipes")[0]]
    for r in recipes:
        md = to_markdown(r)
        data = {**r, **urls(r)}
        (OUT / "recipes" / f"{r['slug']}.md").write_text(md, encoding="utf-8")
        (OUT / "recipes" / f"{r['slug']}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        entries.append(index_entry(r))
        full += ["---", "", md]

    (OUT / "index.json").write_text(json.dumps(
        {"site": SITE_URL, "count": len(entries), "recipes": entries},
        ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [LLMS_HEADER.format(site=SITE_URL)]
    for e in entries:
        lines.append(f"- [{e['title']}]({e['md_url']}) ({e['title_ru']}): {', '.join(e['course'])}; "
                     f"{', '.join(e['main_ingredients'])}; {e['time_total_min']} min")
    (OUT / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")

    items = "\n".join(
        f'<li><a href="recipes/{html.escape(e["slug"])}.md">{html.escape(e["title"])}</a> '
        f'(<a href="recipes/{html.escape(e["slug"])}.json">json</a>) — '
        f'{html.escape(", ".join(e["tags"]))}</li>' for e in entries)
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


if __name__ == "__main__":
    main()
