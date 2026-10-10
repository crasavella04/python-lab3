"""Конфигурация Sphinx + MyST.

Сборка (как в CI):  sphinx-build -W --keep-going -b dirhtml docs site
  -W            — предупреждения считаются ошибками (аналог mkdocs build --strict)
  -b dirhtml    — адреса вида /t1/ вместо /t1.html (такие же, как были у MkDocs)
"""

import os
import shutil
from pathlib import Path

# -- Проект ------------------------------------------------------------------
project = "Результаты исследований"
author = "crasavella04"
copyright = "тексты — CC BY 4.0, код — MIT, данные — CC0"
language = "ru"

# Адрес зависит от площадки: в CI передаётся через SITE_URL (GitHub Pages, Helios, GitVerse Pages)
html_baseurl = os.environ.get("SITE_URL", "https://crasavella04.github.io/python-lab3/")

extensions = [
    "myst_parser",
    "sphinx_design",          # вкладки, сетки
    "sphinx_sitemap",         # sitemap.xml; даты <lastmod> — из истории Git
]

# -- MyST --------------------------------------------------------------------
myst_enable_extensions = ["dollarmath", "amsmath", "colon_fence", "deflist", "attrs_block"]
myst_heading_anchors = 3

# Сгенерированные фрагменты T2 вставляются через {include}, отдельными страницами не собираются
exclude_patterns = ["_build", "t2/results/*.md", "_extra"]

# -- HTML --------------------------------------------------------------------
html_theme = "furo"
html_title = project
html_static_path = ["_static"]
html_extra_path = ["_extra"]          # файлы как есть: переадресация /theory/ → /t1/
templates_path = ["_templates"]
html_copy_source = False              # не публиковать исходники страниц (_sources)
html_show_sourcelink = False
html_last_updated_fmt = "%d.%m.%Y"
html_last_updated_use_utc = True

# Формулы: KaTeX из репозитория (T4: сайт не должен зависеть от внешних CDN).
# sphinxcontrib-katex не подошёл: CSS и шрифты он по умолчанию берёт с jsDelivr.
# Разметку формул делает штатный код sphinx.ext.mathjax, а рендерит её наш KaTeX (см. setup()).
html_math_renderer = "katex_local"
html_css_files = ["katex/katex.min.css"]
html_js_files = ["katex/katex.min.js", "katex/auto-render.min.js", "katex-init.js"]

# sitemap.xml с адресами той площадки, под которую идёт сборка; <lastmod> — дата коммита страницы
sitemap_url_scheme = "{link}"
sitemap_locales = [None]
sitemap_show_lastmod = True
sitemap_excludes = ["search/", "genindex/"]

# -- Метаданные для шаблонов (_templates/page.html) ---------------------------
html_context = {
    "build": {
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "target": os.environ.get("DEPLOY_TARGET", "local"),
    },
    "citation": {
        "authors": [{"name": "crasavella04", "orcid": ""}],   # заменить на ФИО и ORCID
        "institution": "Университет ИТМО",
        "doi": "",                                            # DOI архива в Zenodo
        "repository": "https://github.com/crasavella04/python-lab3",
        "license": {
            "text": "https://creativecommons.org/licenses/by/4.0/",
            "code": "https://opensource.org/license/mit",
            "data": "https://creativecommons.org/publicdomain/zero/1.0/",
        },
        # Наборы данных для schema.org Dataset (Google Dataset Search), по имени документа
        "datasets": {
            "t2/index": {
                "name": "Фактическое покрытие 95%-го t-интервала для среднего (Монте-Карло)",
                "description": "Доля доверительных интервалов, накрывших истинное среднее, для четырёх "
                               "распределений и объёмов выборки 5–100, по 20 000 повторений.",
                "csv": "results/coverage.csv",
                "variables": ["dist", "n", "coverage"],
            },
        },
    },
}

# -- Проверка внешних ссылок (стадия lint, P1) -------------------------------
linkcheck_timeout = 20
linkcheck_retries = 2
linkcheck_ignore = [
    r"https?://127\.0\.0\.1.*",
    r"https?://localhost.*",
    r"https://example\.org/.*",
]


# -- Файлы результатов T2 по их постоянным адресам ---------------------------
def _copy_t2_results(app, exception):
    """CSV, SVG и манифест T2 должны лежать по адресу /t2/results/…: на них ссылаются
    страница, JSON-LD Dataset и manifest.json. Sphinx сам копирует только картинки (в _images)."""
    if exception or app.builder.format != "html":
        return
    src = Path(app.srcdir) / "t2" / "results"
    dest = Path(app.outdir) / "t2" / "results"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ["coverage.csv", "coverage.svg", "manifest.json"]:
        shutil.copy2(src / name, dest / name)


def _unicode_section_ids(app, doctree):
    """Якоря разделов из текста заголовка с кириллицей (#методика) вместо порядковых (#id1).

    Sphinx/docutils выбрасывают из id не-ASCII символы и нумеруют разделы: id1, id2…
    Такие якоря сдвигаются при добавлении раздела и ломают внешние ссылки (T5).
    Явные метки MyST (`(label)=`) не трогаем; старый idN остаётся вторым id раздела.
    """
    import re
    from docutils import nodes

    used = set()
    for section in doctree.findall(nodes.section):
        ids = section["ids"]
        if not ids or not all(re.fullmatch(r"id\d+", i) for i in ids):
            continue
        title = section.next_node(nodes.title).astext().lower()
        slug = re.sub(r"[^\w\s-]", "", title)
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        if not slug:
            continue
        candidate, n = slug, 1
        while candidate in used or candidate in doctree.ids:
            candidate, n = f"{slug}-{n}", n + 1
        used.add(candidate)
        ids.insert(0, candidate)
        doctree.ids[candidate] = section


def setup(app):
    app.connect("doctree-read", _unicode_section_ids)
    # Разметка формул как у MathJax (\( \), \[ \], номера уравнений), но без подключения MathJax:
    # скрипт MathJax Sphinx добавляет, только когда выбран рендерер "mathjax"
    app.setup_extension("sphinx.ext.mathjax")
    from sphinx.ext.mathjax import html_visit_displaymath, html_visit_math
    app.add_html_math_renderer("katex_local", (html_visit_math, None), (html_visit_displaymath, None))
    app.connect("build-finished", _copy_t2_results)
