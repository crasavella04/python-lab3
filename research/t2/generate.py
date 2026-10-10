"""Стратегия «вычисления отдельно»: расчёт → CSV, Markdown, SVG и manifest.json в каталог сайта.

    python generate.py [--out КАТАЛОГ] [--n-sim N]

По умолчанию результаты пишутся в docs/t2/results и коммитятся вместе с манифестом;
CI только проверяет манифест (provenance.py check) и собирает сайт.
"""

import argparse
import json
import platform
import time
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "lab3"  # стабильные id в SVG → воспроизводимый хеш файла

from experiment.coverage import Params, load_dataset, plot, run  # noqa: E402
from provenance import code_state, data_state, git_state, sha256, sha256_json  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent.parent / "docs" / "t2" / "results"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--n-sim", type=int, default=Params().n_sim)
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    p = Params(n_sim=args.n_sim)
    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    df = run(p, load_dataset())
    elapsed = time.perf_counter() - t0

    table = df.pivot(index="n", columns="dist", values="coverage")[p.dists]
    df.to_csv(out / "coverage.csv", index=False, lineterminator="\n")
    (out / "coverage.md").write_text(
        table.to_markdown(floatfmt=".3f") + "\n", encoding="utf-8", newline="\n")
    plot(df, p.alpha).savefig(out / "coverage.svg", metadata={"Date": None})

    outputs = {f: sha256(out / f) for f in ["coverage.csv", "coverage.md", "coverage.svg"]}
    params = asdict(p)
    data = data_state()
    manifest = {
        "experiment": "t-interval coverage",
        "git": git_state(),
        "code": code_state(),
        "data": {k: data[k] for k in ["file", "version", "sha256", "rows", "source"]},
        "params": params,
        "params_sha256": sha256_json(params),
        "env": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            **{pkg: version(pkg) for pkg in ["numpy", "scipy", "pandas", "matplotlib"]},
        },
        "run": {
            "started_utc": started.isoformat(timespec="seconds"),
            "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "compute_seconds": round(elapsed, 2),
        },
        "outputs": outputs,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    # Короткая сводка для вставки на страницу сайта
    m = manifest
    (out / "provenance.md").write_text(
        "| Что | Значение |\n|---|---|\n"
        f"| Коммит кода | `{m['git']['commit'][:7]}`{' (есть незакоммиченные правки!)' if m['git']['dirty'] else ''} |\n"
        f"| Хеш кода эксперимента | `{m['code']['sha256'][:16]}` |\n"
        f"| Датасет | `{m['data']['file']}` v{m['data']['version']}, SHA-256 `{m['data']['sha256'][:16]}` |\n"
        f"| Параметры | n_sim = {p.n_sim}, seed = {p.seed}, α = {p.alpha}; хеш `{m['params_sha256'][:16]}` |\n"
        f"| Окружение | Python {m['env']['python']}, numpy {m['env']['numpy']}, scipy {m['env']['scipy']} |\n"
        f"| Запуск | {m['run']['finished_utc']}, расчёт {m['run']['compute_seconds']} с |\n",
        encoding="utf-8", newline="\n")
    print(f"Готово за {elapsed:.1f} с → {out}")


if __name__ == "__main__":
    main()
