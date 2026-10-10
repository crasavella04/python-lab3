"""Вес страницы about/ в вариантах local и cdn (см. cdn_experiment.py).

Списки ресурсов — то, что браузер реально запросил (performance.getEntriesByType('resource')),
без общих для обоих вариантов поиска и sitemap и без виджета api.github.com.
Свои файлы считаются в gzip -9 (так их отдают GitHub Pages и Helios), внешние — скачиваются
с Accept-Encoding: gzip, br и User-Agent браузера (Google Fonts отдаёт разное разным браузерам).
"""

import gzip
import json
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
COMPRESSED = {".html", ".css", ".js", ".json", ".xml", ".svg"}

COMMON = ["about/index.html", "assets/stylesheets/main.ec1eaa64.min.css",
          "assets/stylesheets/palette.ab4e12ef.min.css", "assets/javascripts/bundle.d7400e89.min.js"]
VARIANTS = {
    "local": COMMON + [
        "assets/katex/katex.min.css", "assets/katex/katex.min.js", "assets/katex/auto-render.min.js",
        "javascripts/katex-init.js", "assets/katex/fonts/KaTeX_Main-Regular.woff2",
        "assets/katex/fonts/KaTeX_Math-Italic.woff2", "assets/katex/fonts/KaTeX_Size2-Regular.woff2",
    ],
    "cdn": COMMON + [
        "https://fonts.googleapis.com/css?family=Roboto:300,300i,400,400i,700,700i%7CRoboto+Mono:400,400i,700,700i&display=fallback",
        "https://fonts.gstatic.com/s/roboto/v51/KFO5CnqEu92Fr1Mu53ZEC9_Vu3r1gIhOszmkBnka.woff2",
        "https://fonts.gstatic.com/s/roboto/v51/KFO7CnqEu92Fr1ME7kSn66aGLdTylUAMa3iUBGEe.woff2",
        "https://fonts.gstatic.com/s/roboto/v51/KFO7CnqEu92Fr1ME7kSn66aGLdTylUAMa3yUBA.woff2",
        "https://fonts.gstatic.com/s/robotomono/v31/L0x5DF4xlVMF-BfR8bXMIjhPq3-OXg.woff2",
        "https://fonts.gstatic.com/s/robotomono/v31/L0x5DF4xlVMF-BfR8bXMIjhLq38.woff2",
        "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js",
        "https://cdn.jsdelivr.net/npm/mathjax@3/es5/output/chtml/fonts/woff-v2/MathJax_Zero.woff",
        "https://cdn.jsdelivr.net/npm/mathjax@3/es5/output/chtml/fonts/woff-v2/MathJax_Main-Regular.woff",
        "https://cdn.jsdelivr.net/npm/mathjax@3/es5/output/chtml/fonts/woff-v2/MathJax_Math-Italic.woff",
        "https://cdn.jsdelivr.net/npm/mathjax@3/es5/output/chtml/fonts/woff-v2/MathJax_Size2-Regular.woff",
    ],
}


def local_size(variant: str, path: str) -> int:
    data = (OUT / variant / path).read_bytes()
    return len(gzip.compress(data, 9)) if Path(path).suffix in COMPRESSED else len(data)


def remote_size(url: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, br"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return len(r.read())  # urllib не распаковывает: это байты, переданные по сети


def group(path: str) -> str:
    if path in COMMON:
        return "страница и тема"
    if "font" in path or path.endswith((".woff", ".woff2")) and "katex" not in path.lower() and "MathJax" not in path:
        return "шрифт текста"
    return "формулы"


def main():
    result = {}
    for variant, paths in VARIANTS.items():
        rows = []
        for p in paths:
            size = remote_size(p) if p.startswith("http") else local_size(variant, p)
            g = "формулы" if ("katex" in p.lower() or "mathjax" in p.lower()) else group(p)
            rows.append({"resource": p, "group": g, "bytes": size, "external": p.startswith("http")})
        totals = {}
        for r in rows:
            totals[r["group"]] = totals.get(r["group"], 0) + r["bytes"]
        result[variant] = {
            "requests": len(rows),
            "external_requests": sum(r["external"] for r in rows),
            "total_kb": round(sum(r["bytes"] for r in rows) / 1024, 1),
            "by_group_kb": {k: round(v / 1024, 1) for k, v in totals.items()},
            "rows": rows,
        }
        print(variant, {k: v for k, v in result[variant].items() if k != "rows"})
    (Path(__file__).with_name("page_weight.json")).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
