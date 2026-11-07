#!/usr/bin/env python3
"""Собирает сайт рецептов для AI-агентов из recipes/*.json в _site/.

Без внешних зависимостей. Запуск: python3 scripts/build.py
Базовый URL берётся из SITE_URL (по умолчанию GitHub Pages репозитория).
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
            errors.append(f"{path.name}: невалидный JSON: {e}")
            continue
        missing = [k for k in REQUIRED if k not in r]
        if missing:
            errors.append(f"{path.name}: нет полей {missing}")
        if r.get("slug") != path.stem:
            errors.append(f"{path.name}: slug '{r.get('slug')}' не совпадает с именем файла")
        recipes.append(r)
    if errors:
        sys.exit("Ошибки в рецептах:\n" + "\n".join(errors))
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
        g = f"{i['grams']} г"
        parts.append(f"({g})" if parts else g)
    amount = " ".join(parts)
    line = f"{i['name']} — {amount}" if amount else i["name"]
    if i.get("note"):
        line += f"; {i['note']}"
    if i.get("optional"):
        line += " (по желанию)"
    return line


def to_markdown(r):
    u = urls(r)
    t = r["time_min"]
    out = [f"# {r['title']}", ""]
    if r.get("title_en"):
        out += [f"*{r['title_en']}*", ""]
    out += [r["summary"], ""]
    if u["image_url"]:
        out += [f"![{r['title']}]({u['image_url']})", ""]
    out += [
        f"- **Порций:** {r['servings']}" + (f" (выход ≈{r['yield_g']} г)" if r.get("yield_g") else ""),
        f"- **Время:** {t.get('total')} мин (подготовка {t.get('prep')}, готовка {t.get('cook')})",
        f"- **Тип:** {', '.join(r['course'])}" + (f"; кухня: {r['cuisine']}" if r.get("cuisine") else ""),
    ]
    if r.get("diet"):
        out.append(f"- **Диета:** {', '.join(r['diet'])}")
    if r.get("method"):
        out.append(f"- **Способ:** {', '.join(r['method'])}")
    out.append(f"- **Теги:** {', '.join(r['tags'])}")
    n = r.get("nutrition")
    if n:
        extra = f", клетчатка {n['fiber_g']} г" if "fiber_g" in n else ""
        out.append(f"- **КБЖУ ({n['basis']}):** {n['kcal']} ккал, Б {n['protein_g']} г, "
                   f"Ж {n['fat_g']} г, У {n['carbs_g']} г{extra}" + (" — оценка" if n.get("estimated") else ""))
    out += ["", f"## Ингредиенты (на {r['servings']} порц.)", ""]
    group = None
    for i in r["ingredients"]:
        if i.get("group") and i["group"] != group:
            group = i["group"]
            out += ["", f"**{group}**", ""]
        out.append(f"- {fmt_ing(i)}")
    out += ["", "## Список покупок", ""]
    for s in r["shopping_list"]:
        line = f"- [ ] {s['item']} — {s['qty']}"
        if s.get("alt"):
            line += f" (или: {s['alt']})"
        out.append(line)
    out += ["", "## Приготовление", ""]
    out += [f"{n}. {s}" for n, s in enumerate(r["steps"], 1)]
    if r.get("tips"):
        out += ["", "## Советы", ""] + [f"- {x}" for x in r["tips"]]
    if r.get("storage"):
        out += ["", f"**Хранение:** {r['storage']}"]
    src = r["source"]
    out += ["", "## Источник", "", f"- Видео: {src['url']}" + (f" ({src['channel']})" if src.get("channel") else "")]
    if src.get("recipe_url"):
        out.append(f"- Рецепт автора: {src['recipe_url']}")
    if src.get("note"):
        out.append(f"- {src['note']}")
    out += ["", f"JSON: {u['json_url']}", ""]
    return "\n".join(out)


def index_entry(r):
    n = r.get("nutrition") or {}
    return {
        "slug": r["slug"],
        "title": r["title"],
        "title_en": r.get("title_en"),
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


LLMS_HEADER = """# Рецепты (база для AI-агентов)

> Личная база проверенных рецептов с граммовками, списками покупок, КБЖУ и фото готового блюда. Все рецепты на русском.

Как пользоваться:
- Найти рецепт: загрузить {site}/index.json (все рецепты с тегами, основными продуктами, временем и ккал) и отфильтровать по полям `tags`, `main_ingredients`, `course`, `diet`, `method`.
- Всё сразу одним файлом: {site}/llms-full.txt
- Конкретный рецепт: `md_url` (Markdown) или `json_url` (структурированные данные).
- Если пользователь в магазине — отдавать раздел «Список покупок» (`shopping_list`). Если готовит — «Ингредиенты» и «Приготовление».
- Масштабирование порций: граммовки указаны на `servings` порций; пересчитывать пропорционально, специи — осторожнее.
- Картинка готового блюда: `image_url` (PNG), можно показывать пользователю.

## Рецепты
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
    full = [LLMS_HEADER.format(site=SITE_URL).split("## Рецепты")[0]]
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
        lines.append(f"- [{e['title']}]({e['md_url']}): {', '.join(e['course'])}; "
                     f"{', '.join(e['main_ingredients'])}; {e['time_total_min']} мин")
    (OUT / "llms.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")

    items = "\n".join(
        f'<li><a href="recipes/{html.escape(e["slug"])}.md">{html.escape(e["title"])}</a> '
        f'(<a href="recipes/{html.escape(e["slug"])}.json">json</a>) — '
        f'{html.escape(", ".join(e["tags"]))}</li>' for e in entries)
    (OUT / "index.html").write_text(f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Рецепты</title>
<link rel="alternate" type="text/plain" href="llms.txt">
<link rel="alternate" type="application/json" href="index.json">
</head><body>
<h1>Рецепты</h1>
<p>База рецептов для AI-агентов. Начните с <a href="llms.txt">llms.txt</a>,
полный список — <a href="index.json">index.json</a>, всё одним файлом — <a href="llms-full.txt">llms-full.txt</a>.</p>
<ul>
{items}
</ul>
</body></html>
""", encoding="utf-8")
    print(f"Собрано рецептов: {len(entries)} → {OUT}")


if __name__ == "__main__":
    main()
