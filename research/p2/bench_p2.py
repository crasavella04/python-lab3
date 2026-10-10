"""Время сборки страницы-стресс-теста на трёх генераторах (P2): прогрев + 3 холодные сборки.

    python bench_p2.py   # → build_times.json
"""

import json
import os
import shutil
import statistics
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITES = HERE / "sites"
T1 = HERE.parent / "t1" / ".venvs"
ENV = {**os.environ, "PYTHONUTF8": "1", "NODE_OPTIONS": "--dns-result-order=ipv4first"}

GENS = {
    "sphinx": ([T1 / "sphinx/Scripts/sphinx-build.exe", "-q", "-b", "html", ".", "_build/html"], ["_build"]),
    "mkdocs": ([HERE / ".venvs/mkdocs/Scripts/mkdocs.exe", "build", "-q"], ["site"]),
    # шаблон темы (_build/templates) не удаляем: это одноразовая загрузка 125 МБ, а не сборка
    "jupyterbook": ([T1 / "jb/Scripts/jupyter-book.exe", "build", "--html"],
                    ["_build/html", "_build/site", "_build/temp", "_build/cache"]),
}


def build(gen):
    cmd, _ = GENS[gen]
    t0 = time.perf_counter()
    p = subprocess.run([str(c) for c in cmd], cwd=SITES / gen, env=ENV, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    dt = time.perf_counter() - t0
    if p.returncode:
        print((p.stdout + p.stderr)[-2000:])
        raise SystemExit(f"{gen}: сборка упала")
    return dt, p.stdout + p.stderr


def main():
    res = {}
    for gen, (_, clean) in GENS.items():
        _, log = build(gen)  # прогрев: шаблоны, кэш байткода
        warnings = [l for l in log.splitlines() if any(k in l for k in ("WARNING", "⚠", "⛔", "warning"))]
        runs = []
        for _ in range(3):
            for c in clean:
                shutil.rmtree(SITES / gen / c, ignore_errors=True)
            runs.append(round(build(gen)[0], 2))
        if gen == "jupyterbook":
            # Обходной путь: {iframe} не копирует локальный HTML графика Plotly — кладём его вручную
            shutil.copy2(SITES / gen / "coverage_plotly.html", SITES / gen / "_build/html/stress/coverage_plotly.html")
        res[gen] = {"cold_s": statistics.median(runs), "runs": runs, "warnings": warnings[:20]}
        print(gen, res[gen]["cold_s"], runs, f"предупреждений: {len(warnings)}")
        for w in warnings[:8]:
            print("   ", w[:160])
    (HERE / "build_times.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
