"""P5: версии сайта по git-тегам vX.Y — sphinx-polyversion, алиас latest и versions.json.

    python scripts/build_versions.py site     # вызывается из `nox -s build` после сборки main

Корень сайта (site/) — сборка текущей ветки (main): её делает nox до этого скрипта.
Здесь к ней добавляются:
  site/vX.Y/        — каждая версия, собранная из своего тега: выгрузка тега во временный
                      каталог, расчёт P3 (research/p3/pipeline.py этого тега, по его данным),
                      затем sphinx-build с conf.py этого же тега;
  site/latest/      — копия новейшей версии: постоянный адрес «последний выпуск»;
  site/versions.json — список версий для переключателя (docs/_static/versions.js).

Почему sphinx-polyversion, а не sphinx-multiversion: последний (0.2.4, 2020) и его форк
sphinx-multiversion-contrib падают на Sphinx 9 (Config.read() стал принимать параметры только
по имени), а ещё собирают каждый тег с conf.py текущей ветки. Подробно — в отчёте P5.
"""

import asyncio
import json
import os
import re
import shutil
import sys
from pathlib import Path

from sphinx_polyversion.driver import DefaultDriver
from sphinx_polyversion.environment import Environment
from sphinx_polyversion.git import Git, file_predicate
from sphinx_polyversion.sphinx import CommandBuilder, Placeholder

ROOT = Path(__file__).resolve().parent.parent
TAG = r"v\d+\.\d+"      # тег версии: v1.0, v1.1, v2.0 …


class InCheckout(Environment):
    """Команды — в каталоге выгрузки тега. Базовый Environment запускает их в текущем каталоге,
    и `research/p3/pipeline.py` посчитал бы данные main, а не тега."""

    async def run(self, *cmd, **kwargs):
        kwargs.setdefault("cwd", self.path)
        return await super().run(*cmd, **kwargs)


class Driver(DefaultDriver):
    failed: list = []

    def build_failed(self, rev, exc_info):
        # По умолчанию ошибка только пишется в журнал, и сайт вышел бы без версии. Здесь — падение.
        super().build_failed(rev, exc_info)
        err = exc_info[1].__cause__
        print(f"ВЕРСИЯ {rev.name}: сборка не удалась\n{getattr(err, 'stdout', '')}\n{getattr(err, 'stderr', '')}",
              file=sys.stderr)
        self.failed.append(rev.name)

    async def build_root(self):
        pass   # корень — сборка main; versions.json пишем сами (ниже), со своим форматом


def version_key(name):
    return tuple(int(x) for x in re.findall(r"\d+", name))


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "site").resolve()
    # Расчёт P3 в каждой версии — со своим кэшем по содержимому: общий каталог, разные ключи
    os.environ.setdefault("P3_CACHE", str(ROOT / ".cache" / "p3"))

    builder = CommandBuilder(
        Path("docs"),
        [sys.executable, "-m", "sphinx", "-W", "--keep-going", "-q", "-b", "dirhtml",
         Placeholder.SOURCE_DIR, Placeholder.OUTPUT_DIR],
        pre_cmd=[sys.executable, "research/p3/pipeline.py"],
    )
    driver = Driver(
        ROOT, out,
        # Только теги vX.Y; ветки здесь не нужны — main уже собран в корень
        vcs=Git(branch_regex=r"(?!)", tag_regex=TAG, predicate=file_predicate([Path("docs/conf.py")])),
        builder=builder,
        env=InCheckout.factory(),
        # Это попадёт в POLYVERSION_DATA → docs/conf.py: имя версии, коммит тега
        data_factory=lambda drv, rev, env: {"name": rev.name, "commit": rev.obj, "date": rev.date.isoformat()},
    )
    driver.run(sequential=True)
    if driver.failed:
        sys.exit(f"P5: не собраны версии {', '.join(driver.failed)}")

    tags = sorted(driver.builds, key=lambda t: version_key(t.name), reverse=True)
    versions = [{"name": "", "path": "", "title": "main (в разработке)"}]
    if tags:
        latest = tags[0]
        # latest — копия, а не переадресация: у каждой страницы постоянный адрес latest/…
        shutil.rmtree(out / "latest", ignore_errors=True)
        shutil.copytree(out / latest.name, out / "latest")
        versions.append({"name": "latest", "path": "latest/", "title": f"latest ({latest.name})",
                         "target": latest.name})
    for t in tags:
        versions.append({"name": t.name, "path": f"{t.name}/", "title": t.name,
                         "commit": t.obj, "date": t.date.isoformat()})
    (out / "versions.json").write_text(json.dumps(
        {"latest": tags[0].name if tags else None, "versions": versions}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n")
    print(f"P5: версии {[t.name for t in tags] or 'нет тегов'}; latest → {tags[0].name if tags else '—'}")


if __name__ == "__main__":
    main()
