"""Исходные данные P3: время отклика системы в трёх режимах работы (мс).

    python make_dataset.py 1.0     # 300 измерений: по 100 на режим
    python make_dataset.py 1.1     # то же + новая партия из 80 измерений режима C после обновления ПО

Генерация детерминирована (фиксированные seed), поэтому версия набора данных однозначно задаёт
файл. Паспорт DATASET.json хранит версию и SHA-256; pipeline.py отказывается считать, если файл
не совпадает с паспортом (данные изменили, а версию — нет).
"""

import csv
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VERSIONS = {
    "1.0": "исходные измерения: по 100 в режимах A, B, C",
    "1.1": "добавлена партия из 80 измерений режима C после обновления ПО (отклик быстрее)",
}


def batch(regime, n, mu, sigma, seed, batch_id):
    rnd = random.Random(seed)
    # логнормальное время отклика: положительное, с правым хвостом, как у реальных задержек
    return [{"regime": regime, "batch": batch_id, "ms": round(rnd.lognormvariate(mu, sigma), 2)} for _ in range(n)]


def build(version):
    rows = (batch("A", 100, 4.0, 0.25, 11, 1)
            + batch("B", 100, 4.3, 0.30, 12, 1)
            + batch("C", 100, 4.6, 0.35, 13, 1))
    if version >= "1.1":
        rows += batch("C", 80, 4.1, 0.30, 14, 2)
    return rows


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else "1.0"
    if version not in VERSIONS:
        sys.exit(f"нет версии {version}: {', '.join(VERSIONS)}")
    rows = build(version)
    out = HERE / "measurements.csv"
    with out.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=["regime", "batch", "ms"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    passport = {
        "file": "research/p3/data/measurements.csv",
        "version": version,
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "rows": len(rows),
        "changes": VERSIONS[version],
        "source": "синтетика: логнормальное время отклика, research/p3/data/make_dataset.py",
        "license": "CC0-1.0",
    }
    (HERE / "DATASET.json").write_text(json.dumps(passport, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8", newline="\n")
    print(f"measurements.csv v{version}: {len(rows)} строк, sha256 {passport['sha256'][:12]}")


if __name__ == "__main__":
    main()
