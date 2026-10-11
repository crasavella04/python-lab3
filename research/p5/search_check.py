"""P5: проверка русского поиска на словоформах, которых нет в тексте сайта.

    python research/p5/search_check.py site     # site — собранный сайт (nox -s build)

Для каждого запроса:
  * форма запроса и все однокоренные формы, которые реально есть в тексте сайта;
  * какие страницы находит поиск Sphinx «как есть» (Snowball) и с дополнением docs/_static/search-ru.js
    (у основы запроса отрезается глагольный суффикс -ова-/-ыва-/…).

Поиск воспроизведён по searchtools.js Sphinx 9: основа запроса ищется в терминах индекса и
заголовков точно, а если точного нет — как подстрока терминов (частичное совпадение).
Результаты сверены с поиском в браузере (таблица в отчёте P5).
"""

import json
import re
import sys
from pathlib import Path

import snowballstemmer

QUERIES = {
    # запрос: (что проверяет, корень для поиска однокоренных форм в тексте)
    "воспроизводимых": ("падеж и число прилагательного", "воспроизв"),
    "надёжный": ("род прилагательного и буква ё", "надёжн"),
    "версионный": ("производное слово: в тексте только «версионирование»", "версион"),
    "кэшировать": ("инфинитив: в тексте «кэширует», «кэширование»", "кэшир"),
    "откатывать": ("глагол несовершенного вида: в тексте «откат», «откатил»", "откат"),
}
SUFFIXES = ["ирова", "ова", "ева", "ыва", "ива"]   # как в docs/_static/search-ru.js
MIN_STEM = 4


def trim(stem):
    for s in SUFFIXES:
        if len(stem) - len(s) >= MIN_STEM and stem.endswith(s):
            return stem[: -len(s)]
    return stem


def site_words(site):
    """Словоформы основного текста страниц (как их видит читатель), без версий vX.Y и latest."""
    words = {}
    for f in site.glob("**/index.html"):
        rel = f.relative_to(site).as_posix()
        if re.match(r"(v\d|latest)", rel):
            continue
        html = f.read_text(encoding="utf-8")
        m = re.search(r"<article.*?</article>", html, re.S)
        if not m:
            continue
        text = re.sub(r"<(script|style)\b.*?</\1>", " ", m.group(0), flags=re.S)
        for w in re.findall(r"[а-яё]+", re.sub(r"<[^>]+>", " ", text).lower()):
            words.setdefault(w, set()).add(rel.rsplit("/", 2)[0] if "/" in rel else "/")
    return words


def search(index, stem):
    """Документы, которые найдёт searchtools.js для одной основы (без ранжирования)."""
    found = set()
    for kind in ("terms", "titleterms"):
        terms = index[kind]
        hits = [terms[stem]] if stem in terms else (
            [v for k, v in terms.items() if stem in k] if len(stem) > 2 else [])
        for v in hits:
            found.update(v if isinstance(v, list) else [v])
    return sorted(index["docnames"][i] for i in found)


def main():
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    text = (site / "searchindex.js").read_text(encoding="utf-8")
    index = json.loads(text[text.index("(") + 1:text.rindex(")")])
    words = site_words(site)
    st = snowballstemmer.stemmer("russian")
    rows = []
    for q, (what, root) in QUERIES.items():
        stem = st.stemWord(q)
        forms = sorted(w for w in words if w.startswith(root.replace("ё", "е")) or w.startswith(root))
        rows.append({
            "query": q, "what": what, "in_text": q in words, "forms": forms,
            "stem": stem, "found": search(index, stem),
            "stem_p5": trim(stem), "found_p5": search(index, trim(stem)),
        })
    for r in rows:
        print(f"{r['query']} ({r['what']})")
        print(f"   форма запроса в тексте: {'ЕСТЬ — запрос не годится' if r['in_text'] else 'нет'}; "
              f"однокоренные в тексте: {', '.join(r['forms'])}")
        print(f"   Snowball:        «{r['stem']}» → {r['found'] or 'ничего'}")
        print(f"   + search-ru.js:  «{r['stem_p5']}» → {r['found_p5'] or 'ничего'}")
    out = Path(__file__).with_name("search_check.json")
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    if any(r["in_text"] for r in rows):
        sys.exit("форма запроса встречается в тексте — замените запрос")


if __name__ == "__main__":
    main()
