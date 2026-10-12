"""Пакет данных исследований для файлового хранилища на Helios (челлендж: свой action).

    python scripts/data_package.py data-package     # собрать каталог; выкладывает CI действием helios-upload

Внутри: наборы данных T2 и P3 с паспортами, итоговая таблица T2, CITATION.cff, лицензия данных,
SHA256SUMS для проверки целостности и index.html со списком файлов (листинг каталогов на Helios
выключен). Пакет полностью определяется содержимым репозитория: повторная сборка даёт те же байты.
"""

import hashlib
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = {
    "t2/measurements.csv": "research/t2/data/measurements.csv",
    "t2/DATASET.json": "research/t2/data/DATASET.json",
    "t2/coverage.csv": "docs/t2/results/coverage.csv",
    "t2/manifest.json": "docs/t2/results/manifest.json",
    "p3/measurements.csv": "research/p3/data/measurements.csv",
    "p3/DATASET.json": "research/p3/data/DATASET.json",
    "CITATION.cff": "CITATION.cff",
}
LICENSE = """Data in this package are dedicated to the public domain under CC0 1.0:
https://creativecommons.org/publicdomain/zero/1.0/
Source: https://github.com/crasavella04/python-lab3
"""


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data-package")
    shutil.rmtree(out, ignore_errors=True)
    for dst, src in FILES.items():
        (out / dst).parent.mkdir(parents=True, exist_ok=True)
        # LF везде: суммы не должны зависеть от того, на какой ОС собран пакет
        (out / dst).write_bytes((ROOT / src).read_bytes().replace(b"\r\n", b"\n"))
    (out / "LICENSE.txt").write_text(LICENSE, encoding="utf-8", newline="\n")

    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    sums = [f"{hashlib.sha256((out / f).read_bytes()).hexdigest()}  {f}" for f in files]
    (out / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")

    def version(name):
        return json.loads((out / name).read_text(encoding="utf-8")).get("version", "")

    rows = "\n".join(
        f'<tr><td><a href="{html.escape(f)}">{html.escape(f)}</a></td>'
        f'<td>{(out / f).stat().st_size}</td></tr>' for f in files + ["SHA256SUMS"])
    (out / "index.html").write_text(f"""<!doctype html>
<html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Данные исследований python-lab3</title>
<style>body{{font-family:system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem}}
td{{padding:.2rem .8rem .2rem 0}}td:last-child{{text-align:right}}</style>
<h1>Данные исследований python-lab3</h1>
<p>Наборы данных T2 (версия {version("t2/DATASET.json")}) и P3 (версия {version("p3/DATASET.json")}),
лицензия CC0. Отчёты — на <a href="../python-lab3/">сайте</a>, исходники — на
<a href="https://github.com/crasavella04/python-lab3">GitHub</a>.
Проверка целостности: <code>sha256sum -c SHA256SUMS</code>.</p>
<table><tr><th align="left">Файл</th><th align="right">Байт</th></tr>
{rows}
</table>
""", encoding="utf-8", newline="\n")
    print(f"Пакет данных: {len(files)} файлов → {out}")


if __name__ == "__main__":
    main()
