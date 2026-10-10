"""Проверка русской орфографии по собранному сайту (стадия lint).

    python scripts/spellcheck.py site

Проверяется текст статей в собранном HTML: так в проверку не попадают код, формулы, адреса,
зато попадает текст, вставленный через {include}. Словарь — Hunspell ru_RU из LibreOffice
(tools/spelling, лицензия BSD) через spylls — реализацию Hunspell на чистом Python, без системных
библиотек. Термины, которых нет в словаре, перечислены в tools/spelling/wordlist.txt
(одно слово в строке; «слово*» — все слова с этим началом).

Код выхода 1, если найдены неизвестные слова.
"""

import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

from spylls.hunspell import Dictionary

ROOT = Path(__file__).resolve().parent.parent
DICT = ROOT / "tools" / "spelling" / "ru_RU"
WORDLIST = ROOT / "tools" / "spelling" / "wordlist.txt"
SKIP_TAGS = {"code", "pre", "script", "style", "kbd", "samp"}
SKIP_CLASSES = {"math", "headerlink", "katex"}
WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)*")


class ArticleText(HTMLParser):
    """Собирает текст внутри <article>, пропуская код, формулы и ссылки-якоря."""

    def __init__(self):
        super().__init__()
        self.in_article = 0
        self.skip_stack = []
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "article":
            self.in_article += 1
        classes = set((a.get("class") or "").split())
        if tag in SKIP_TAGS or classes & SKIP_CLASSES:
            self.skip_stack.append(tag)
        elif self.skip_stack:
            self.skip_stack.append(tag)

    def handle_endtag(self, tag):
        if self.skip_stack:
            self.skip_stack.pop()
        elif tag == "article":
            self.in_article -= 1

    def handle_data(self, data):
        if self.in_article and not self.skip_stack:
            self.chunks.append(data)


def load_wordlist():
    exact, prefixes = set(), []
    for line in WORDLIST.read_text(encoding="utf-8").splitlines():
        w = line.split("#", 1)[0].strip().lower()
        if not w:
            continue
        (prefixes.append(w[:-1]) if w.endswith("*") else exact.add(w))
    return exact, tuple(prefixes)


def main():
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    d = Dictionary.from_files(str(DICT))
    exact, prefixes = load_wordlist()
    cache = {}

    def known(word):
        low = word.lower()
        if low in exact or (prefixes and low.startswith(prefixes)):
            return True
        if low not in cache:
            cache[low] = d.lookup(word) or d.lookup(low)
        return cache[low]

    unknown = defaultdict(Counter)
    pages = sorted(p for p in site.rglob("index.html")
                   if not {"_static", "search", "genindex", "_sources"} & set(p.relative_to(site).parts))
    for page in pages:
        parser = ArticleText()
        parser.feed(page.read_text(encoding="utf-8"))
        for token in WORD.findall(" ".join(parser.chunks)):
            parts = [token] if known(token) else token.split("-")
            for part in parts:
                if part and not known(part):
                    unknown[part.lower()][str(page.parent.relative_to(site)) or "/"] += 1

    print(f"Проверено страниц: {len(pages)}, неизвестных слов: {len(unknown)}")
    for word in sorted(unknown):
        where = ", ".join(f"{p} ×{n}" if n > 1 else p for p, n in unknown[word].items())
        print(f"  {word}: {where}")
    sys.exit(1 if unknown else 0)


if __name__ == "__main__":
    main()
