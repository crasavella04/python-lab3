"""Замеры конвейеров «эксперимент → артефакт → страница» на одном эксперименте.

    python bench_pipelines.py          # → pipelines.json

A  manual     — скрипт сохраняет PNG, его вручную кладут в docs/ (базовый вариант)
B  nbconvert  — jupyter nbconvert --execute → HTML и Markdown
C  myst-nb    — исполнение ноутбука при сборке Sphinx с кэшем jupyter-cache
D  papermill  — параметризованные запуски ноутбука (n_sim) → nbconvert в Markdown
E  script     — generate.py (CSV, MD, SVG, manifest) через nox
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "pipelines" / "out"
PY = HERE / ".venv" / "Scripts" / "python.exe"
SPHINX = HERE.parent / "t1" / ".venvs" / "sphinx" / "Scripts" / "sphinx-build.exe"
NB = HERE / "notebooks" / "coverage.ipynb"
# MPLBACKEND не задаём: Agg в ядре ноутбука отключает вывод графиков (рисунок пропадает из Markdown)
ENV = {**os.environ, "PYTHONUTF8": "1", "PYDEVD_DISABLE_FILE_VALIDATION": "1"}

results = {}


def sh(*cmd, cwd=HERE) -> float:
    t0 = time.perf_counter()
    p = subprocess.run([str(c) for c in cmd], cwd=cwd, env=ENV, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    dt = time.perf_counter() - t0
    if p.returncode:
        print((p.stdout + p.stderr)[-2500:])
        raise SystemExit(f"упало: {' '.join(map(str, cmd))}")
    return round(dt, 2)


def size_kb(*paths: Path) -> float:
    total = 0
    for p in paths:
        total += sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) if p.is_dir() else p.stat().st_size
    return round(total / 1024, 1)


def record(key, **kw):
    results[key] = kw
    print(key, kw)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)

    # A. Ручное сохранение картинки
    d = OUT / "manual"
    d.mkdir()
    code = ("import sys; sys.path.insert(0, '.'); from experiment.coverage import run, plot; "
            f"plot(run()).savefig(r'{d / 'coverage.png'}', dpi=150)")
    record("A_manual", seconds=sh(PY, "-c", code), output_kb=size_kb(d), files=1)

    # B. nbconvert --execute
    d = OUT / "nbconvert"
    t_html = sh(PY, "-m", "nbconvert", "--to", "html", "--execute", NB, "--output-dir", d)
    t_md = sh(PY, "-m", "nbconvert", "--to", "markdown", "--execute", NB, "--output-dir", d / "md")
    record("B_nbconvert", seconds_html=t_html, seconds_md=t_md,
           html_kb=size_kb(d / "coverage.html"), md_kb=size_kb(d / "md"),
           md_files=sum(1 for f in (d / "md").rglob("*") if f.is_file()))

    # C. MyST-NB с кэшем
    proj = HERE / "pipelines" / "mystnb"
    shutil.copy(NB, proj / "coverage.ipynb")
    for x in ["_build", ".jupyter_cache"]:
        shutil.rmtree(proj / x, ignore_errors=True)
    build = [SPHINX, "-q", "-b", "html", ".", "_build/html"]
    cold = sh(*build, cwd=proj)
    warm = sh(*build, "-E", cwd=proj)  # всё перечитать: ноутбук берётся из кэша
    nb = json.loads((proj / "coverage.ipynb").read_text(encoding="utf-8"))
    cell = next(c for c in nb["cells"] if "parameters" in c["metadata"].get("tags", []))
    cell["source"] = "".join(cell["source"]).replace("n_sim = 20_000", "n_sim = 20_001")
    (proj / "coverage.ipynb").write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    changed = sh(*build, cwd=proj)
    record("C_mystnb", seconds_cold=cold, seconds_cached=warm, seconds_after_param_change=changed,
           cache_kb=size_kb(proj / ".jupyter_cache"), site_kb=size_kb(proj / "_build" / "html"))

    # D. papermill: параметризованные запуски
    d = OUT / "papermill"
    d.mkdir()  # papermill сам каталог не создаёт
    runs = {}
    for n_sim in [2_000, 20_000, 200_000]:
        nb_out = d / f"coverage_nsim{n_sim}.ipynb"
        t = sh(PY, "-m", "papermill", NB, nb_out, "-p", "n_sim", n_sim, "--log-level", "WARNING")
        sh(PY, "-m", "nbconvert", "--to", "markdown", nb_out, "--output-dir", d / "md")
        runs[n_sim] = {"seconds": t, "ipynb_kb": size_kb(nb_out)}
    record("D_papermill", runs=runs)

    # E. Скрипт generate.py: напрямую и через nox (первый запуск создаёт окружение)
    d = OUT / "script"
    direct = sh(PY, "generate.py", "--out", d)
    nox = [PY, "-m", "nox", "-s", "results", "--", "--out", OUT / "nox"]
    shutil.rmtree(HERE / ".nox", ignore_errors=True)
    nox_first = sh(*nox)
    nox_reuse = sh(*nox)
    record("E_script", seconds_direct=direct, seconds_nox_first=nox_first, seconds_nox_reuse=nox_reuse,
           output_kb=size_kb(d), files=sorted(f.name for f in d.iterdir()))

    (HERE / "pipelines.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
