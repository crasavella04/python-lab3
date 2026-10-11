"""P3: данные → расчёт → график и таблица для сайта, с кэшем по содержимому.

    python research/p3/pipeline.py            # вызывается из `nox -s site` перед сборкой Sphinx

Кэш: ключ — SHA-256 от данных, этого скрипта и параметров. Если такой результат уже посчитан
(каталог .cache/p3/<ключ>), файлы просто копируются в docs/p3/generated, а numpy и matplotlib
даже не импортируются: проверка кэша работает на стандартной библиотеке. Если ключ новый — расчёт.
В CI каталог .cache/p3 сохраняется между запусками через actions/cache.

Метка версии (коммит, дата сборки) в кэшированные файлы не попадает: иначе каждый коммит
сбрасывал бы кэш. Её подставляет Sphinx при сборке (docs/conf.py).
"""

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DATA = HERE / "data" / "measurements.csv"
PASSPORT = HERE / "data" / "DATASET.json"
OUT = ROOT / "docs" / "p3" / "generated"
# P5: версии сайта собираются из выгрузок тегов во временных каталогах; P3_CACHE даёт им общий кэш
CACHE = Path(os.environ["P3_CACHE"]) if os.environ.get("P3_CACHE") else ROOT / ".cache" / "p3"
PARAMS = {"bootstrap": 20_000, "alpha": 0.05, "seed": 7}
OUTPUTS = ["table.md", "summary.csv", "stats.json", "figure.svg"]
KEEP = 5  # сколько результатов хранить в кэше


def norm(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def cache_key() -> str:
    h = hashlib.sha256()
    for part in (norm(DATA), norm(Path(__file__)), json.dumps(PARAMS, sort_keys=True).encode()):
        h.update(hashlib.sha256(part).digest())
    return h.hexdigest()


def check_passport():
    passport = json.loads(PASSPORT.read_text(encoding="utf-8"))
    actual = hashlib.sha256(norm(DATA)).hexdigest()
    if actual != passport["sha256"]:
        sys.exit("P3: файл данных не совпадает с паспортом DATASET.json — данные изменили без новой версии")
    return passport


def compute(dest: Path):
    """Сам расчёт: статистики по режимам и бутстреп-интервалы для среднего и медианы."""
    import csv

    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["svg.hashsalt"] = "p3"
    import matplotlib.pyplot as plt
    import numpy as np

    groups = {}
    with DATA.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            groups.setdefault(r["regime"], []).append(float(r["ms"]))

    rng = np.random.default_rng(PARAMS["seed"])
    lo_q, hi_q = 100 * PARAMS["alpha"] / 2, 100 * (1 - PARAMS["alpha"] / 2)
    stats = {}
    for regime in sorted(groups):
        x = np.array(groups[regime])
        boot = rng.choice(x, size=(PARAMS["bootstrap"], x.size), replace=True)
        means, medians = boot.mean(axis=1), np.median(boot, axis=1)
        stats[regime] = {
            "n": int(x.size),
            "mean": float(x.mean()),
            "mean_ci": [float(np.percentile(means, lo_q)), float(np.percentile(means, hi_q))],
            "median": float(np.median(x)),
            "median_ci": [float(np.percentile(medians, lo_q)), float(np.percentile(medians, hi_q))],
            "p95": float(np.percentile(x, 95)),
        }

    (dest / "stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8", newline="\n")
    with (dest / "summary.csv").open("w", encoding="utf-8", newline="\n") as f:
        f.write("regime,n,mean,mean_ci_low,mean_ci_high,median,median_ci_low,median_ci_high,p95\n")
        for k, s in stats.items():
            f.write(f"{k},{s['n']},{s['mean']:.2f},{s['mean_ci'][0]:.2f},{s['mean_ci'][1]:.2f},"
                    f"{s['median']:.2f},{s['median_ci'][0]:.2f},{s['median_ci'][1]:.2f},{s['p95']:.2f}\n")
    lines = ["| Режим | n | Среднее, мс | 95 % ДИ среднего | Медиана, мс | 95 % ДИ медианы | 95-й перцентиль |",
             "|---|---:|---:|---|---:|---|---:|"]
    for k, s in stats.items():
        lines.append(f"| {k} | {s['n']} | {s['mean']:.1f} | {s['mean_ci'][0]:.1f} – {s['mean_ci'][1]:.1f} | "
                     f"{s['median']:.1f} | {s['median_ci'][0]:.1f} – {s['median_ci'][1]:.1f} | {s['p95']:.1f} |")
    (dest / "table.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    names = list(stats)
    pos = np.arange(len(names))
    ax.boxplot([groups[k] for k in names], positions=pos, widths=0.5, showfliers=False,
               medianprops={"color": "#c77d12"})
    means = [stats[k]["mean"] for k in names]
    err = np.array([[m - stats[k]["mean_ci"][0], stats[k]["mean_ci"][1] - m] for k, m in zip(names, means)]).T
    ax.errorbar(pos + 0.32, means, yerr=err, fmt="o", color="#3f63c8", capsize=4, label="среднее, 95 % ДИ")
    ax.set_xticks(pos, [f"{k}\nn = {stats[k]['n']}" for k in names])
    ax.set_ylabel("время отклика, мс")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(dest / "figure.svg", metadata={"Date": None})


def main():
    t0 = time.perf_counter()
    passport = check_passport()
    key = cache_key()
    entry = CACHE / key
    if (entry / "done").exists():
        status = "hit"
    else:
        status = "miss"
        tmp = CACHE / f"{key}.tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        compute(tmp)
        (tmp / "done").write_text(passport["version"], encoding="utf-8")
        shutil.rmtree(entry, ignore_errors=True)
        tmp.rename(entry)
        # храним только последние результаты: кэш не должен расти бесконечно
        old = sorted((p for p in CACHE.iterdir() if p.is_dir() and not p.name.endswith(".tmp")),
                     key=lambda p: p.stat().st_mtime)[:-KEEP]
        for p in old:
            shutil.rmtree(p, ignore_errors=True)

    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    for name in OUTPUTS:
        shutil.copy2(entry / name, OUT / name)
    # График — под именем с ключом кэша: хостинг разрешает браузеру кэшировать файлы
    # (GitHub Pages: max-age=600), и при неизменном имени после обновления данных читатель
    # до 10 минут видел бы новую таблицу рядом со старым графиком. Новые данные → новый адрес.
    figure = f"figure-{key[:12]}.svg"
    shutil.copy2(entry / "figure.svg", OUT / figure)
    # путь — от docs/: MyST разрешает картинки во вставке {include} относительно страницы, а не вставки
    (OUT / "figure.md").write_text(
        f"![Время отклика по режимам: распределение и среднее с 95 % доверительным интервалом](p3/generated/{figure})\n",
        encoding="utf-8", newline="\n")
    seconds = round(time.perf_counter() - t0, 3)
    (OUT / "run.json").write_text(json.dumps(
        {"cache": status, "key": key, "seconds": seconds, "dataset_version": passport["version"]},
        indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"P3: кэш {'найден' if status == 'hit' else 'не найден, расчёт'} "
          f"(ключ {key[:12]}), данные v{passport['version']}, {seconds} с")


if __name__ == "__main__":
    main()
