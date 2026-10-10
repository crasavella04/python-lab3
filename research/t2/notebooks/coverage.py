# ---
# jupyter:
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Покрытие t-интервала
#
# Фактическая доля 95 %-х доверительных интервалов для среднего, накрывших истинное среднее.

# %% tags=["parameters"]
n_sim = 20_000
dists = ["normal", "exponential", "lognormal", "empirical"]
seed = 2026

# %%
import sys
from pathlib import Path

root = Path.cwd()
while not (root / "experiment").exists():
    root = root.parent
sys.path.insert(0, str(root))

from experiment.coverage import Params, plot, run

p = Params(n_sim=n_sim, dists=list(dists), seed=seed)
df = run(p)

# %%
df.pivot(index="n", columns="dist", values="coverage").round(3)

# %%
# Без `fig` в конце: inline-бэкенд сам выводит фигуру, иначе она попадёт в результат дважды
fig = plot(df)
