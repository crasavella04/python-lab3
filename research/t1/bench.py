"""Замеры сборки четырёх генераторов на одинаковом корпусе (см. make_corpus.py).

    python bench.py check            # одна сборка каждого, вывод ошибок
    python bench.py run [повторы] [генераторы...]   # холодная и инкрементальная сборка, объём результата

Холодная сборка — с удалённым каталогом результата и кэшами генератора.
Инкрементальная — повторная сборка после изменения одной страницы.
Результат пишется в results.json.
"""

import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
SITES = HERE / "sites"
VENVS = HERE / ".venvs"
MAIN_VENV = HERE.parent.parent / ".venv"

GENS = {
    "mkdocs": {
        "cmd": [MAIN_VENV / "Scripts/mkdocs.exe", "build", "-q"],
        "out": "site",
        "clean": ["site"],
        "touch": "docs/pages/page050.md",
    },
    "sphinx": {
        "cmd": [VENVS / "sphinx/Scripts/sphinx-build.exe", "-q", "-b", "html", ".", "_build/html"],
        "out": "_build/html",
        "clean": ["_build"],
        "touch": "pages/page050.md",
    },
    "pelican": {
        "cmd": [VENVS / "pelican/Scripts/pelican.exe", "content", "-o", "output", "-s", "pelicanconf.py", "-q"],
        "out": "output",
        "clean": ["output", "cache"],
        "touch": "content/page050.md",
    },
    "jupyterbook": {
        "cmd": [VENVS / "jb/Scripts/jupyter-book.exe", "build", "--html"],
        "out": "_build/html",
        # шаблон темы (_build/templates) не удаляем: это одноразовая загрузка, а не сборка
        "clean": ["_build/html", "_build/site", "_build/temp", "_build/cache"],
        "touch": "pages/page050.md",
    },
}

# NODE_OPTIONS: тема Jupyter Book слушает localhost по IPv6, а сборщик ходит по IPv4 — без этого HTML-экспорт падает
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "NODE_OPTIONS": "--dns-result-order=ipv4first"}


def build(gen: str, quiet: bool = True) -> float:
    cfg = GENS[gen]
    t0 = time.perf_counter()
    proc = subprocess.run([str(c) for c in cfg["cmd"]], cwd=SITES / gen, env=ENV,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    dt = time.perf_counter() - t0
    if proc.returncode != 0 or not quiet:
        print(f"--- {gen}: код {proc.returncode}, {dt:.2f} с")
        print((proc.stdout + proc.stderr)[-3000:])
    if proc.returncode != 0:
        raise SystemExit(f"сборка {gen} упала")
    return dt


def clean(gen: str) -> None:
    for d in GENS[gen]["clean"]:
        shutil.rmtree(SITES / gen / d, ignore_errors=True)


def touch(gen: str, n: int) -> None:
    page = SITES / gen / GENS[gen]["touch"]
    text = page.read_text(encoding="utf-8").rsplit("\n\nПравка №", 1)[0]
    page.write_text(f"{text}\n\nПравка № {n}.\n", encoding="utf-8", newline="\n")


def size(gen: str) -> tuple[int, int]:
    files = [p for p in (SITES / gen / GENS[gen]["out"]).rglob("*") if p.is_file()]
    return len(files), sum(p.stat().st_size for p in files)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    names = [a for a in sys.argv[2:] if a in GENS]
    gens = names or list(GENS)
    if mode == "check":
        for gen in gens:
            clean(gen)
            build(gen, quiet=False)
        return

    repeats = next((int(a) for a in sys.argv[2:] if a.isdigit()), 3)
    results = {}
    for gen in gens:
        build(gen)  # прогрев: загрузка шаблонов, кэш байткода Python
        cold, incr = [], []
        for r in range(repeats):
            clean(gen)
            cold.append(build(gen))
            touch(gen, r)
            incr.append(build(gen))
        files, total = size(gen)
        results[gen] = {
            "cold_s": round(statistics.median(cold), 2),
            "incremental_s": round(statistics.median(incr), 2),
            "files": files,
            "size_kb": round(total / 1024),
            "runs": {"cold": [round(x, 2) for x in cold], "incremental": [round(x, 2) for x in incr]},
        }
        print(gen, results[gen])
    out = HERE / "results.json"
    old = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    out.write_text(json.dumps({**old, **results}, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
