"""Генерирует одинаковый тестовый корпус для четырёх генераторов статических сайтов.

Корпус = показательная страница (формулы, рисунок, таблицы, сноска, цитата)
+ N страниц-«наполнителей» с русским текстом для замеров времени сборки и проверки поиска.
Синтаксис показательной страницы — родной для каждого генератора, содержание одинаковое.

    python make_corpus.py [N]        # по умолчанию N = 100
"""

import random
import shutil
import sys
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).parent / "sites"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100

# ---------- общий контент ----------

SUBJECTS = ["Серия экспериментов", "Повторное измерение", "Контрольная выборка", "Модель регрессии",
            "Калибровка датчика", "Обработка сигналов", "Оценка погрешности", "Статистический тест"]
VERBS = ["показала", "подтвердила", "опровергла", "уточнила", "выявила", "не обнаружила"]
OBJECTS = ["значимое различие средних", "линейную зависимость отклика", "систематическую ошибку прибора",
           "устойчивость оценок к выбросам", "сходимость итерационного метода", "смещение распределения"]
TAILS = ["при уровне значимости 0,05.", "на всех исследованных режимах.", "после фильтрации шумов.",
         "в пределах доверительного интервала.", "для выборок малого объёма.", "при повторных экспериментах."]

CSV = "Режим,Среднее,СКО,n\nA,12.4,0.8,30\nB,13.1,1.1,30\nC,11.9,0.7,28\n"

BIB = dedent("""\
    @book{knuth1984,
      author    = {Knuth, Donald E.},
      title     = {The {\\TeX}book},
      publisher = {Addison-Wesley},
      year      = {1984}
    }
    """)

SVG = dedent("""\
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 160" width="320" height="160">
      <rect width="320" height="160" fill="#fff"/>
      <polyline fill="none" stroke="#3f51b5" stroke-width="3"
        points="10,150 50,120 90,125 130,90 170,80 210,55 250,50 290,20"/>
      <text x="160" y="155" font-size="12" text-anchor="middle">время, с</text>
    </svg>
    """)


def filler(i: int) -> tuple[str, str]:
    rnd = random.Random(i)
    title = f"Протокол эксперимента {i:03d}"
    paras = []
    for _ in range(6):
        paras.append(" ".join(
            f"{rnd.choice(SUBJECTS)} {rnd.choice(VERBS)} {rnd.choice(OBJECTS)} {rnd.choice(TAILS)}"
            for _ in range(5)))
    return title, "\n\n".join(paras)


# ---------- показательная страница в синтаксисе каждого генератора ----------

SHOWCASE = {
    # MkDocs Material: arithmatex + KaTeX/MathJax, md_in_html для подписи рисунка, footnotes
    "mkdocs": dedent("""\
        # Показательная страница

        Результаты серии экспериментов по измерению отклика.

        ## Формулы

        Выборочное среднее:

        $$
        \\bar{x} = \\frac{1}{n}\\sum_{i=1}^{n} x_i
        $$

        Окружение `align`:

        $$
        \\begin{align}
        s^2 &= \\frac{1}{n-1}\\sum_{i=1}^{n}(x_i-\\bar{x})^2 \\\\
        t   &= \\frac{\\bar{x}-\\mu_0}{s/\\sqrt{n}}
        \\end{align}
        $$

        ## Рисунок

        <figure markdown="span" id="fig-response">
          ![Отклик](response.svg)
          <figcaption>Рис. 1. Отклик системы во времени</figcaption>
        </figure>

        См. [рисунок 1](#fig-response).

        ## Таблица

        | Режим | Среднее | СКО | n |
        |-------|--------:|----:|--:|
        | A | 12.4 | 0.8 | 30 |
        | B | 13.1 | 1.1 | 30 |
        | C | 11.9 | 0.7 | 28 |

        ## Сноска и источник

        Методика взята из классики[^1]. Knuth (1984).

        [^1]: Сноска с пояснением.
        """),
    # Sphinx + MyST: нумерация уравнений, {eq}, {numref}, csv-table, sphinxcontrib-bibtex
    "sphinx": dedent("""\
        # Показательная страница

        Результаты серии экспериментов по измерению отклика.

        ## Формулы

        Выборочное среднее:

        $$
        \\bar{x} = \\frac{1}{n}\\sum_{i=1}^{n} x_i
        $$ (eq-mean)

        Окружение `align`:

        ```{math}
        :label: eq-t
        \\begin{align}
        s^2 &= \\frac{1}{n-1}\\sum_{i=1}^{n}(x_i-\\bar{x})^2 \\\\
        t   &= \\frac{\\bar{x}-\\mu_0}{s/\\sqrt{n}}
        \\end{align}
        ```

        Из {eq}`eq-mean` и {eq}`eq-t` следует критерий.

        ## Рисунок

        ```{figure} response.svg
        :name: fig-response

        Отклик системы во времени
        ```

        См. {numref}`fig-response`.

        ## Таблица

        ```{csv-table} Результаты по режимам
        :file: data.csv
        :header-rows: 1
        :name: tab-results
        ```

        См. {numref}`tab-results`.

        ## Сноска и источник

        Методика взята из классики[^1] {cite:p}`knuth1984`.

        [^1]: Сноска с пояснением.

        ```{bibliography}
        ```
        """),
    # Jupyter Book 2 (mystmd): тот же MyST, ссылки [](#label), цитаты [@key]
    "jupyterbook": dedent("""\
        # Показательная страница

        Результаты серии экспериментов по измерению отклика.

        ## Формулы

        Выборочное среднее:

        $$
        \\bar{x} = \\frac{1}{n}\\sum_{i=1}^{n} x_i
        $$ (eq-mean)

        Окружение `align`:

        ```{math}
        :label: eq-t
        \\begin{align}
        s^2 &= \\frac{1}{n-1}\\sum_{i=1}^{n}(x_i-\\bar{x})^2 \\\\
        t   &= \\frac{\\bar{x}-\\mu_0}{s/\\sqrt{n}}
        \\end{align}
        ```

        Из [](#eq-mean) и [](#eq-t) следует критерий.

        ## Рисунок

        ```{figure} response.svg
        :label: fig-response

        Отклик системы во времени
        ```

        См. [](#fig-response).

        ## Таблица

        ```{csv-table} Результаты по режимам
        :header-rows: 1
        :label: tab-results
        Режим,Среднее,СКО,n
        A,12.4,0.8,30
        B,13.1,1.1,30
        C,11.9,0.7,28
        ```

        См. [](#tab-results).

        ## Сноска и источник

        Методика взята из классики[^1] [@knuth1984].

        [^1]: Сноска с пояснением.
        """),
    # Pelican: Markdown + метаданные; формулы через pelican-render-math (MathJax)
    "pelican": dedent("""\
        Title: Показательная страница
        Date: 2026-10-10
        Slug: showcase

        Результаты серии экспериментов по измерению отклика.

        ## Формулы

        Выборочное среднее:

        $$
        \\bar{x} = \\frac{1}{n}\\sum_{i=1}^{n} x_i
        $$

        Окружение `align`:

        $$
        \\begin{align}
        s^2 &= \\frac{1}{n-1}\\sum_{i=1}^{n}(x_i-\\bar{x})^2 \\\\
        t   &= \\frac{\\bar{x}-\\mu_0}{s/\\sqrt{n}}
        \\end{align}
        $$

        ## Рисунок

        ![Отклик системы во времени]({static}/images/response.svg)

        Рис. 1. Отклик системы во времени

        ## Таблица

        | Режим | Среднее | СКО | n |
        |-------|--------:|----:|--:|
        | A | 12.4 | 0.8 | 30 |
        | B | 13.1 | 1.1 | 30 |
        | C | 11.9 | 0.7 | 28 |

        ## Сноска и источник

        Методика взята из классики[^1]. Knuth (1984).

        [^1]: Сноска с пояснением.
        """),
}

# ---------- конфигурации ----------

CONFIGS = {
    "mkdocs": {
        "mkdocs.yml": dedent("""\
            site_name: SSG benchmark
            theme:
              name: material
              language: ru
            plugins:
              - search:
                  lang: ru
            markdown_extensions:
              - attr_list
              - md_in_html
              - footnotes
              - tables
              - pymdownx.arithmatex:
                  generic: true
            extra_javascript:
              - https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js
            """),
    },
    "sphinx": {
        "conf.py": dedent("""\
            project = "SSG benchmark"
            language = "ru"
            extensions = ["myst_parser", "sphinx_design", "sphinxcontrib.bibtex"]
            myst_enable_extensions = ["dollarmath", "amsmath", "colon_fence"]
            myst_heading_anchors = 3
            numfig = True
            math_numfig = True
            bibtex_bibfiles = ["refs.bib"]
            html_theme = "furo"
            exclude_patterns = ["_build"]
            """),
    },
    "jupyterbook": {
        "myst.yml": dedent("""\
            version: 1
            project:
              title: SSG benchmark
              numbering:
                figure: true
                equation: true
                table: true
              bibliography:
                - refs.bib
              toc:
                - file: index.md
                - file: showcase.md
                - pattern: "pages/*.md"
            site:
              template: book-theme
            """),
    },
    "pelican": {
        "pelicanconf.py": dedent("""\
            AUTHOR = "bench"
            SITENAME = "SSG benchmark"
            SITEURL = ""
            PATH = "content"
            STATIC_PATHS = ["images"]
            TIMEZONE = "Europe/Moscow"
            DEFAULT_LANG = "ru"
            DEFAULT_DATE = (2026, 10, 10)
            FEED_ALL_ATOM = None
            CATEGORY_FEED_ATOM = None
            PLUGINS = ["pelican.plugins.render_math"]
            MARKDOWN = {"extension_configs": {
                "markdown.extensions.extra": {},
                "markdown.extensions.toc": {},
            }}
            CACHE_CONTENT = True
            LOAD_CONTENT_CACHE = True
            """),
    },
}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    for gen in SHOWCASE:
        site = ROOT / gen
        shutil.rmtree(site, ignore_errors=True)
        for name, text in CONFIGS[gen].items():
            write(site / name, text)

        if gen == "pelican":
            content = site / "content"
            write(content / "showcase.md", SHOWCASE[gen])
            write(content / "images" / "response.svg", SVG)
            for i in range(1, N + 1):
                title, body = filler(i)
                write(content / f"page{i:03d}.md",
                      f"Title: {title}\nDate: 2026-10-10\nSlug: page{i:03d}\n\n{body}\n")
            continue

        docs = site / "docs" if gen == "mkdocs" else site
        write(docs / "showcase.md", SHOWCASE[gen])
        write(docs / "response.svg", SVG)
        write(docs / "data.csv", CSV)
        write(docs / "refs.bib", BIB)
        index = "# Тестовый сайт\n\nКорпус для сравнения генераторов.\n"
        if gen == "sphinx":
            index += "\n```{toctree}\n:maxdepth: 1\n:glob:\n\nshowcase\npages/*\n```\n"
        write(docs / "index.md", index)
        for i in range(1, N + 1):
            title, body = filler(i)
            write(docs / "pages" / f"page{i:03d}.md", f"# {title}\n\n{body}\n")

    print(f"Корпус: {len(SHOWCASE)} генератора × (1 показательная + {N} страниц) → {ROOT}")


if __name__ == "__main__":
    main()
