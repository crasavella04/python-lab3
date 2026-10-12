# python-lab3 — генераторы статических сайтов для публикации результатов

[![GitHub Actions](https://github.com/crasavella04/python-lab3/actions/workflows/pages.yml/badge.svg?branch=main)](https://github.com/crasavella04/python-lab3/actions/workflows/pages.yml)
[![GitVerse CI](https://gitverse.ru/api/repos/crasavella04/python-lab3/actions/workflows/site.yml/badge.svg?branch=main&lang=ru)](https://gitverse.ru/crasavella04/python-lab3/cicd?workflow=site.yml&workflowName=Сайт)

Лабораторная работа 3 курса РРиИД Python: сайт с отчётами об исследовании генераторов
статических сайтов и автоматизации их публикации.

**Сайт:** [GitHub Pages](https://crasavella04.github.io/python-lab3/) ·
[Helios ИТМО](https://se.ifmo.ru/~s564180/python-lab3/)

| | |
|---|---|
| Генератор | Sphinx 9.1 + MyST-Parser, тема Furo (выбор обоснован в T1) |
| Исходники страниц | `docs/` (Markdown/MyST), конфигурация — `docs/conf.py` |
| CI/CD | GitHub Actions — `.github/workflows/pages.yml` (GitHub Pages, Helios); GitVerse — `.gitverse/workflows/site.yml` (GitVerse Pages, P1) |
| Исследования | `research/t1` … `research/t4`: скрипты замеров и экспериментов |

## Локальная сборка

```bash
python -m virtualenv .venv
source .venv/bin/activate                              # Windows: .venv\Scripts\Activate.ps1
pip install --require-hashes -r requirements.txt
sphinx-build -W --keep-going -b dirhtml docs site      # строгая сборка
python scripts/spellcheck.py site                      # орфография
sphinx-build -b linkcheck docs _build/linkcheck        # внешние ссылки
```

## Лицензии

Тексты — CC BY 4.0 (`LICENSE-CONTENT`), код — MIT (`LICENSE`), данные — CC0 1.0
(`research/t2/data/DATASET.json`). Как цитировать — `CITATION.cff`.
