"""Сборка сайта одной командой: данные → результат → сайт (P3).

    python -m nox -s site      # расчёт P3 (с кэшем) → строгая сборка Sphinx → орфография   [по умолчанию]
    python -m nox -s build     # расчёт P3 → строгая сборка → версии по тегам (без орфографии; для Helios)
    python -m nox -s results   # только расчёт P3

Сессии работают в текущем окружении (python=False): зависимости уже стоят из requirements.txt
с проверкой хешей, второе окружение nox только замедлило бы CI. Все команды запускаются тем же
интерпретатором, что и nox (sys.executable): просто "python" взял бы первый Python из PATH,
а это может быть совсем другая версия без нужных пакетов.
"""

import sys

import nox

nox.options.sessions = ["site"]
PY = sys.executable


@nox.session(python=False)
def results(session):
    session.run(PY, "research/p3/pipeline.py")


@nox.session(python=False)
def build(session):
    results(session)
    session.run(PY, "-m", "sphinx", "-W", "--keep-going", "-b", "dirhtml", "docs", "site")
    # P5: версии по тегам vX.Y в site/vX.Y/, алиас site/latest/, site/versions.json
    session.run(PY, "scripts/build_versions.py", "site")


@nox.session(python=False)
def site(session):
    build(session)
    session.run(PY, "scripts/spellcheck.py", "site")
