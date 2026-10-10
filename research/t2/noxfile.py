"""Конвейер «скрипт → Markdown/CSV → сайт» на nox (аналог Makefile, но кроссплатформенный).

    nox -s results      # пересчитать эксперимент и манифест (локально, не в CI)
    nox -s check        # проверить, что результаты соответствуют коду и данным (в CI)
    nox -s docs         # собрать сайт (в CI)
"""

from pathlib import Path

import nox

nox.options.default_venv_backend = "uv"
nox.options.reuse_existing_virtualenvs = True

ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS = ROOT / "docs" / "t2" / "results"


@nox.session(python="3.13")
def results(session):
    session.install("numpy", "scipy", "pandas", "matplotlib", "tabulate")
    session.run("python", "generate.py", *session.posargs)


@nox.session(python=False)
def check(session):
    session.run("python", "provenance.py", "check", str(RESULTS))


@nox.session(python=False)
def docs(session):
    session.notify("check")
    session.run("mkdocs", "build", "--strict", "-f", str(ROOT / "mkdocs.yml"))
