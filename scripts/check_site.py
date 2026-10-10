"""Проверка развёрнутого сайта: не только «открывается ли», но и что именно выкачено.

Использование:
    python scripts/check_site.py <base_url> [--commit SHA] [--target NAME]

Проверяется:
  1. HTTP 200 на ключевых страницах и ассетах;
  2. контрольная строка <meta name="build-marker"> (и совпадение коммита, если задан);
  3. поиск: search/search_index.json доступен и содержит все страницы;
  4. формулы: KaTeX и его шрифты отдаются с того же хоста, в HTML нет ссылок на внешние CDN.

Только стандартная библиотека — скрипт запускается в CI без установки зависимостей.
"""

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PAGES = ["", "t1/", "t2/", "t3/", "t4/", "t5/", "practice/", "about/", "debugging/", "license/"]
# Старые адреса, которые должны продолжать работать (страница перенесена → переадресация)
REDIRECTS = {"theory/": "../t1/"}
ASSETS = [
    "assets/katex/katex.min.js",
    "assets/katex/auto-render.min.js",
    "assets/katex/katex.min.css",
    "assets/katex/fonts/KaTeX_Main-Regular.woff2",
    "javascripts/katex-init.js",
]

failures = []


def check(ok, message):
    print(("  OK   " if ok else "  FAIL ") + message)
    if not ok:
        failures.append(message)


def fetch(url, retries=3):
    """Возвращает (код ответа, тело). Повторяет запрос: хостинг может обновляться не мгновенно."""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            status, body = e.code, b""
        except urllib.error.URLError as e:
            status, body = 0, str(e.reason).encode()
        if attempt < retries - 1:
            time.sleep(5)
    return status, body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    parser.add_argument("--commit", help="ожидаемый коммит в build-marker")
    parser.add_argument("--target", help="ожидаемая площадка в build-marker")
    args = parser.parse_args()

    base = args.base_url.rstrip("/") + "/"
    host = urllib.parse.urlsplit(base).netloc
    print(f"Проверка {base}")

    print("[1] Коды ответа HTTP")
    html = {}
    for page in PAGES:
        status, body = fetch(base + page)
        check(status == 200, f"{status} {base + page}")
        html[page] = body.decode("utf-8", "replace")
    status, _ = fetch(base + "no-such-page-xyz/")
    check(status == 404, f"{status} несуществующая страница отдаёт 404")

    for old, target in REDIRECTS.items():
        status, body = fetch(base + old)
        ok = status == 200 and f'url={target}' in body.decode("utf-8", "replace")
        check(ok, f"{status} {old} переадресует на {target}")

    print("[2] Контрольная строка")
    marker = re.search(r'<meta name="build-marker" content="([^"]+)"', html[""])
    check(marker is not None, f"build-marker найден: {marker.group(1) if marker else '-'}")
    if marker:
        _, commit, target = marker.group(1).split(":")
        if args.commit:
            check(commit == args.commit, f"коммит сборки {commit} == {args.commit}")
        if args.target:
            check(target == args.target, f"площадка {target} == {args.target}")
    check("Результаты исследований" in html[""], "заголовок сайта на главной")

    print("[3] Поиск")
    status, body = fetch(base + "search/search_index.json")
    check(status == 200, f"{status} search/search_index.json")
    try:
        locations = {d["location"].split("#")[0] for d in json.loads(body)["docs"]}
        missing = [p for p in PAGES if p not in locations]
        check(not missing, f"в индексе {len(locations)} страниц, пропущены: {missing or 'нет'}")
    except (ValueError, KeyError) as e:
        check(False, f"индекс поиска не разобран: {e}")
    check("search" in html[""] and "data-md-component=\"search\"" in html[""], "форма поиска на странице")

    print("[4] Формулы и внешние CDN")
    for asset in ASSETS:
        status, _ = fetch(base + asset)
        check(status == 200, f"{status} {asset}")
    check('class="arithmatex"' in html["about/"], "формулы размечены на странице about/")
    external = set()
    for page, text in html.items():
        for tag in re.findall(r"<(?:script|link)\b[^>]*>", text):
            # Учитываем только то, что браузер загружает. <link rel="canonical|license|schema.DC">
            # — метаданные со ссылками на внешние адреса, а не ресурсы страницы
            rel = re.search(r'rel="([^"]+)"', tag)
            if tag.startswith("<link") and not (rel and set(rel.group(1).split()) &
                                                {"stylesheet", "preload", "modulepreload", "icon"}):
                continue
            src = re.search(r'(?:src|href)="([^"]+)"', tag)
            netloc = urllib.parse.urlsplit(src.group(1)).netloc if src else ""
            if netloc and netloc != host:
                external.add(src.group(1))
    check(not external, f"скрипты и стили только с {host}: {sorted(external) or 'внешних нет'}")

    print()
    if failures:
        print(f"Провалено проверок: {len(failures)}")
        sys.exit(1)
    print("Все проверки пройдены")


if __name__ == "__main__":
    main()
