"""Одна и та же страница-стресс-тест на трёх генераторах (P2).

    python make_sites.py        # → sites/{sphinx,mkdocs,jupyterbook}

Каждый генератор настроен так, как рекомендует его документация: где она предлагает CDN
(MathJax, шрифты, Plotly) — используется CDN. Так метрики показывают поведение по умолчанию.
"""

import shutil
from pathlib import Path
from textwrap import dedent

import csv

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
SITES = HERE / "sites"

ROWS = {}
with open(HERE.parent.parent / "docs" / "t2" / "results" / "coverage.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        ROWS.setdefault(int(r["n"]), {})[r["dist"]] = f'{float(r["coverage"]):.3f}'
NS = [5, 20, 100]
DISTS = ["normal", "exponential", "lognormal", "empirical"]

TITLE = "Стресс-тест научного контента"
INTRO = ("Страница проверяет, как генератор справляется с научным контентом: нумерованной формулой, "
         "таблицей с объединёнными ячейками, статическим и интерактивным графиками, листингом кода, "
         "цитированием из BibTeX, двухколоночной вёрсткой, сноской и перекрёстной ссылкой.")
MODEL_TEXT = "Для выборки объёма $n$ доверительный интервал для среднего строится по формуле Стьюдента"
FOOTNOTE = "Стьюдент — псевдоним У. С. Госсета, химика пивоварни Guinness."
TABLE_CAPTION = "Фактическое покрытие 95 %-го t-интервала"
FIG_CAPTION = "Фактическое покрытие t-интервала в зависимости от объёма выборки"
CODE_CAPTION = "Оценка покрытия методом Монте-Карло"
TWO_COL = ("Слева — текст, справа — иллюстрация. На узком экране колонки должны встать друг под "
           "другом, а не сжиматься до нечитаемой ширины. Здесь проверяется именно это: при асимметричных "
           "распределениях покрытие ниже номинала, и разница видна на графике справа.")
CONCLUSION = ("Чем сильнее асимметрия распределения, тем дальше покрытие от номинала при малых выборках. "
              "Это прямо следует из предпосылок формулы, разобранных в разделе")
LISTING = (ASSETS / "listing.py").read_text(encoding="utf-8")
PLOTLY_DIV = (ASSETS / "plotly_div.html").read_text(encoding="utf-8")


def html_table(caption: str) -> str:
    """Таблица с объединёнными ячейками в HTML (rowspan/colspan) — для генераторов без своего синтаксиса."""
    # Без отступов: строка HTML с 4 пробелами в начале для Markdown — блок кода, а не таблица
    lines = ["<table>"]
    if caption:
        lines.append(f"<caption>{caption}</caption>")
    lines += [
        "<thead>",
        '<tr><th rowspan="2">n</th><th>Симметричное</th><th colspan="3">Асимметричные</th></tr>',
        "<tr><th>normal</th><th>exponential</th><th>lognormal</th><th>empirical</th></tr>",
        "</thead>",
        "<tbody>",
        *(f"<tr><td>{n}</td>" + "".join(f"<td>{ROWS[n][d]}</td>" for d in DISTS) + "</tr>" for n in NS),
        "</tbody>",
        "</table>",
    ]
    return "\n".join(lines)


def rst_grid_table() -> str:
    """Та же таблица в виде grid-таблицы reStructuredText: объединения поддерживаются нативно."""
    w = [5, 14, 13, 11, 11]
    line = lambda ch: "+" + "+".join(ch * x for x in w) + "+"
    cell = lambda t, x: " " + t.ljust(x - 1)
    span = w[2] + w[3] + w[4] + 2
    rows = [
        line("-"),
        "|" + cell("n", w[0]) + "|" + cell("Симметричное", w[1]) + "|" + cell("Асимметричные", span) + "|",
        "|" + " " * w[0] + "+" + "+".join("-" * x for x in w[1:]) + "+",
        "|" + " " * w[0] + "|" + "|".join(cell(d, x) for d, x in zip(DISTS, w[1:])) + "|",
        line("="),
    ]
    for n in NS:
        rows.append("|" + cell(str(n), w[0]) + "|" + "|".join(cell(ROWS[n][d], x) for d, x in zip(DISTS, w[1:])) + "|")
        rows.append(line("-"))
    return "\n".join(rows)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def copy_assets(dest: Path, names):
    for n in names:
        shutil.copy2(ASSETS / n, dest / n)


# ---------------------------------------------------------------- Sphinx + MyST
def sphinx():
    d = SITES / "sphinx"
    write(d / "conf.py", dedent("""\
        project = "P2 Sphinx"
        language = "ru"
        extensions = ["myst_parser", "sphinx_design", "sphinxcontrib.bibtex"]
        myst_enable_extensions = ["dollarmath", "amsmath", "colon_fence"]
        numfig = True
        math_numfig = True
        bibtex_bibfiles = ["refs.bib"]
        html_theme = "furo"
        exclude_patterns = ["_build"]
        """))
    write(d / "index.md", "# P2\n\n```{toctree}\nstress\n```\n")
    grid = "\n".join("   " + r for r in rst_grid_table().splitlines())
    write(d / "stress.md", f"""# {TITLE}

{INTRO}

(model)=
## Модель

{MODEL_TEXT}[^student]:

$$
\\bar{{x}} \\pm t_{{1-\\alpha/2,\\,n-1}}\\,\\frac{{s}}{{\\sqrt{{n}}}}
$$ (eq-ci)

Интервал {{eq}}`eq-ci` точен только для нормального распределения {{cite:p}}`student1908`.

[^student]: {FOOTNOTE}

## Результаты

```{{eval-rst}}
.. table:: {TABLE_CAPTION}
   :name: tab-coverage

{grid}
```

## Графики

```{{figure}} coverage.png
:name: fig-coverage

{FIG_CAPTION}
```

Тот же результат интерактивно:

```{{raw}} html
{PLOTLY_DIV}
```

## Код

```{{code-block}} python
:linenos:
:caption: {CODE_CAPTION}

{LISTING}```

## Две колонки

::::{{grid}} 1 1 2 2
:::{{grid-item}}
{TWO_COL}
:::
:::{{grid-item}}
```{{image}} coverage.png
:alt: {FIG_CAPTION}
```
:::
::::

## Выводы

{CONCLUSION} [«Модель»](#model) (формула {{eq}}`eq-ci`, таблица {{numref}}`tab-coverage`, {{numref}}`fig-coverage`).

## Литература

```{{bibliography}}
```
""")
    copy_assets(d, ["coverage.png", "refs.bib"])


# ---------------------------------------------------------------- MkDocs Material
def mkdocs():
    d = SITES / "mkdocs"
    write(d / "mkdocs.yml", dedent("""\
        site_name: P2 MkDocs
        theme:
          name: material
          language: ru
        plugins:
          - search
          - bibtex:
              bib_file: docs/refs.bib
        markdown_extensions:
          - attr_list
          - md_in_html
          - footnotes
          - tables
          - pymdownx.arithmatex:
              generic: true
          - pymdownx.highlight:
              linenums: true
              anchor_linenums: true
          - pymdownx.superfences
          - pymdownx.blocks.caption
        # Формулы — как в документации Material: MathJax с unpkg и конфиг с нумерацией (tags: ams)
        extra_javascript:
          - javascripts/mathjax.js
          - https://unpkg.com/mathjax@3/es5/tex-mml-chtml.js
        """))
    write(d / "docs" / "javascripts" / "mathjax.js", dedent("""\
        window.MathJax = {
          tex: { inlineMath: [["\\\\(", "\\\\)"]], displayMath: [["\\\\[", "\\\\]"]],
                 processEscapes: true, processEnvironments: true, tags: "ams" },
          options: { ignoreHtmlClass: ".*|", processHtmlClass: "arithmatex" }
        };
        document$.subscribe(() => { MathJax.startup.output.clearCache(); MathJax.typesetClear();
                                    MathJax.texReset(); MathJax.typesetPromise(); });
        """))
    write(d / "docs" / "index.md", "# P2\n\n[Стресс-тест](stress.md)\n")
    write(d / "docs" / "stress.md", f"""# {TITLE}

{INTRO}

## Модель {{#model}}

{MODEL_TEXT}[^student]:

$$
\\begin{{equation}}
\\bar{{x}} \\pm t_{{1-\\alpha/2,\\,n-1}}\\,\\frac{{s}}{{\\sqrt{{n}}}}
\\label{{eq-ci}}
\\end{{equation}}
$$

Интервал $\\eqref{{eq-ci}}$ точен только для нормального распределения [@student1908].

[^student]: {FOOTNOTE}

## Результаты

{html_table("Таблица 1. " + TABLE_CAPTION)}

## Графики

![{FIG_CAPTION}](coverage.png)

/// caption
Рис. 1. {FIG_CAPTION}
///

Тот же результат интерактивно:

{PLOTLY_DIV}

## Код

```python title="{CODE_CAPTION}"
{LISTING}```

## Две колонки

<div class="grid" markdown>

{TWO_COL}

![{FIG_CAPTION}](coverage.png)

</div>

## Выводы

{CONCLUSION} [«Модель»](#model) (формула $\\eqref{{eq-ci}}$, таблица 1, рис. 1).

## Литература

\\bibliography
""")
    copy_assets(d / "docs", ["coverage.png", "refs.bib"])


# ---------------------------------------------------------------- Jupyter Book 2
def jupyterbook():
    d = SITES / "jupyterbook"
    write(d / "myst.yml", dedent("""\
        version: 1
        project:
          title: P2 Jupyter Book
          numbering:
            figure: true
            equation: true
            table: true
            code: true
          bibliography:
            - refs.bib
          toc:
            - file: index.md
            - file: stress.md
        site:
          template: book-theme
        """))
    write(d / "index.md", "# P2\n\n[Стресс-тест](stress.md)\n")
    write(d / "stress.md", f"""# {TITLE}

{INTRO}

(model)=
## Модель

{MODEL_TEXT}[^student]:

$$
\\bar{{x}} \\pm t_{{1-\\alpha/2,\\,n-1}}\\,\\frac{{s}}{{\\sqrt{{n}}}}
$$ (eq-ci)

Интервал [](#eq-ci) точен только для нормального распределения [@student1908].

[^student]: {FOOTNOTE}

## Результаты

:::{{table}} {TABLE_CAPTION}
:label: tab-coverage
{html_table("")}
:::

## Графики

```{{figure}} coverage.png
:label: fig-coverage

{FIG_CAPTION}
```

Тот же результат интерактивно:

```{{iframe}} coverage_plotly.html
:width: 100%
```

## Код

```{{code}} python
:linenos:
:caption: {CODE_CAPTION}
{LISTING}```

## Две колонки

::::{{grid}} 1 1 2 2
:::{{grid-item}}
{TWO_COL}
:::
:::{{grid-item}}
![{FIG_CAPTION}](coverage.png)
:::
::::

## Выводы

{CONCLUSION} [«Модель»](#model) (формула [](#eq-ci), таблица [](#tab-coverage), [](#fig-coverage)).
""")
    copy_assets(d, ["coverage.png", "refs.bib", "coverage_plotly.html"])


if __name__ == "__main__":
    shutil.rmtree(SITES, ignore_errors=True)
    sphinx(); mkdocs(); jupyterbook()
    print("Сайты:", sorted(p.name for p in SITES.iterdir()))
