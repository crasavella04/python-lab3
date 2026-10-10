"""Общие материалы страницы-стресс-теста P2 для всех генераторов.

    python make_assets.py      # → assets/: coverage.png, coverage_plotly.html, plotly_div.html, refs.bib, listing.py

Данные — результаты T2 (docs/t2/results/coverage.csv): фактическое покрытие t-интервала.
"""

from pathlib import Path
from textwrap import dedent

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "assets"
OUT.mkdir(exist_ok=True)
df = pd.read_csv(HERE.parent.parent / "docs" / "t2" / "results" / "coverage.csv")

# Статический график matplotlib
fig, ax = plt.subplots(figsize=(6, 3.4), dpi=150)
for dist, g in df.groupby("dist", sort=False):
    ax.plot(g["n"], g["coverage"], marker="o", label=dist)
ax.axhline(0.95, color="grey", ls="--", lw=1, label="номинал")
ax.set_xscale("log")
ax.set_xticks([5, 10, 20, 50, 100], labels=["5", "10", "20", "50", "100"])
ax.set_xlabel("объём выборки n")
ax.set_ylabel("покрытие")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT / "coverage.png")

# Интерактивный график Plotly: библиотека с CDN Plotly — так по умолчанию делает plotly.py
pfig = px.line(df, x="n", y="coverage", color="dist", markers=True, log_x=True,
               labels={"n": "объём выборки n", "coverage": "покрытие", "dist": "распределение"})
pfig.add_hline(y=0.95, line_dash="dash", line_color="grey")
pfig.update_layout(height=380, margin=dict(l=40, r=10, t=10, b=40))
pfig.write_html(OUT / "coverage_plotly.html", include_plotlyjs="cdn", full_html=True)
(OUT / "plotly_div.html").write_text(
    pfig.to_html(include_plotlyjs="cdn", full_html=False, div_id="coverage-plotly",
                  config={"responsive": True}),
    encoding="utf-8")

(OUT / "refs.bib").write_text(dedent("""\
    @article{student1908,
      author  = {Student},
      title   = {The Probable Error of a Mean},
      journal = {Biometrika},
      volume  = {6},
      number  = {1},
      pages   = {1--25},
      year    = {1908},
      doi     = {10.2307/2331554}
    }
    """), encoding="utf-8")

(OUT / "listing.py").write_text(dedent('''\
    def coverage(dist, n, p, data, rng):
        draw, mu = _sampler(dist, data)
        x = draw(rng, (p.n_sim, n))
        mean, sd = x.mean(axis=1), x.std(axis=1, ddof=1)
        half = stats.t.ppf(1 - p.alpha / 2, n - 1) * sd / np.sqrt(n)
        return float(np.mean(np.abs(mean - mu) <= half))
    '''), encoding="utf-8")

print("assets:", sorted(p.name for p in OUT.iterdir()))
