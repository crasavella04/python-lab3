"""Сколько килобайт добавляет на страницу интерактивный график.

Один и тот же точечный график (1000 точек) сохраняется библиотеками Plotly, Bokeh и Altair
в двух вариантах: JS-библиотека подключается с CDN и встроена в страницу (работает офлайн).
Размер gzip — то, что реально передаётся по сети. Результат: viz_cost.json.
"""

import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "viz"
OUT.mkdir(exist_ok=True)

rng = np.random.default_rng(0)
df = pd.DataFrame({"x": rng.normal(size=1000), "y": rng.normal(size=1000)})


def plotly(mode: str) -> Path:
    import plotly.express as px
    path = OUT / f"plotly_{mode}.html"
    px.scatter(df, x="x", y="y").write_html(path, include_plotlyjs="cdn" if mode == "cdn" else True)
    return path


def bokeh(mode: str) -> Path:
    from bokeh.plotting import figure, output_file, save
    from bokeh.resources import CDN, INLINE
    path = OUT / f"bokeh_{mode}.html"
    p = figure(width=500, height=350)
    p.scatter(df.x, df.y)
    output_file(path)
    save(p, resources=CDN if mode == "cdn" else INLINE, title="bokeh")
    return path


def altair(mode: str) -> Path:
    import altair as alt
    path = OUT / f"altair_{mode}.html"
    chart = alt.Chart(df).mark_point().encode(x="x", y="y").interactive()
    chart.save(path, inline=(mode == "inline"))
    return path


def main() -> None:
    results = {}
    for name, fn in [("plotly", plotly), ("bokeh", bokeh), ("altair", altair)]:
        for mode in ["cdn", "inline"]:
            data = fn(mode).read_bytes()
            results[f"{name}_{mode}"] = {
                "kb": round(len(data) / 1024, 1),
                "gzip_kb": round(len(gzip.compress(data, 9)) / 1024, 1),
            }
            print(name, mode, results[f"{name}_{mode}"])
    (Path(__file__).parent / "viz_cost.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
