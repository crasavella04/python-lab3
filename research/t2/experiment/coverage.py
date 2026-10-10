"""Эксперимент: фактическое покрытие 95 %-го t-интервала для среднего.

Для каждого распределения и объёма выборки n генерируется n_sim выборок, по каждой строится
доверительный интервал x̄ ± t(1-α/2, n-1)·s/√n и проверяется, накрыл ли он истинное среднее.
Номинальное покрытие — 0.95; при асимметричных распределениях и малых n оно ниже.

Распределение «empirical» — повторная выборка из датасета data/measurements.csv,
истинное среднее — среднее по датасету.
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DATA = Path(__file__).resolve().parent.parent / "data" / "measurements.csv"


@dataclass
class Params:
    sizes: list[int] = field(default_factory=lambda: [5, 10, 20, 50, 100])
    dists: list[str] = field(default_factory=lambda: ["normal", "exponential", "lognormal", "empirical"])
    n_sim: int = 20_000
    alpha: float = 0.05
    seed: int = 2026


def load_dataset(path: Path = DATA) -> np.ndarray:
    return pd.read_csv(path)["value"].to_numpy()


def _sampler(dist: str, data: np.ndarray):
    """Возвращает (функция генерации выборок формы (n_sim, n), истинное среднее)."""
    match dist:
        case "normal":
            return lambda rng, shape: rng.normal(0.0, 1.0, shape), 0.0
        case "exponential":
            return lambda rng, shape: rng.exponential(1.0, shape), 1.0
        case "lognormal":
            return lambda rng, shape: rng.lognormal(0.0, 1.0, shape), float(np.exp(0.5))
        case "empirical":
            return lambda rng, shape: rng.choice(data, shape, replace=True), float(data.mean())
    raise ValueError(f"неизвестное распределение: {dist}")


def coverage(dist: str, n: int, p: Params, data: np.ndarray, rng: np.random.Generator) -> float:
    draw, mu = _sampler(dist, data)
    x = draw(rng, (p.n_sim, n))
    mean, sd = x.mean(axis=1), x.std(axis=1, ddof=1)
    half = stats.t.ppf(1 - p.alpha / 2, n - 1) * sd / np.sqrt(n)
    return float(np.mean(np.abs(mean - mu) <= half))


def run(p: Params | None = None, data: np.ndarray | None = None) -> pd.DataFrame:
    p = p or Params()
    data = load_dataset() if data is None else data
    rng = np.random.default_rng(p.seed)
    rows = [{"dist": d, "n": n, "coverage": coverage(d, n, p, data, rng)}
            for d in p.dists for n in p.sizes]
    return pd.DataFrame(rows)


def plot(df: pd.DataFrame, alpha: float = 0.05):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for dist, g in df.groupby("dist", sort=False):
        ax.plot(g["n"], g["coverage"], marker="o", label=dist)
    ax.axhline(1 - alpha, color="grey", linestyle="--", linewidth=1, label="номинал")
    ax.set_xscale("log")
    ax.set_xticks(sorted(df["n"].unique()), labels=[str(n) for n in sorted(df["n"].unique())])
    ax.set_xlabel("объём выборки n")
    ax.set_ylabel("фактическое покрытие")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig
