"""Создаёт датасет measurements.csv (версия 1.0): 500 «измерений» с правосторонней асимметрией.

Датасет создаётся один раз и дальше считается внешними данными: эксперимент его только читает,
а в метаданных запуска фиксируются его версия и SHA-256 из паспорта DATASET.json.
Менять данные без новой версии в паспорте нельзя: provenance.py check это поймает.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "1.0"

rng = np.random.default_rng(1)
values = rng.gamma(shape=2.0, scale=3.0, size=500) + rng.normal(0, 0.3, size=500)
out = Path(__file__).with_name("measurements.csv")
pd.DataFrame({"value": values.round(4)}).to_csv(out, index=False, lineterminator="\n")
passport = {
    "file": "data/measurements.csv",
    "version": VERSION,
    "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
    "rows": len(values),
    "source": "синтетика: gamma(2, 3) + N(0, 0.3), seed 1 (data/make_dataset.py)",
}
out.with_name("DATASET.json").write_text(json.dumps(passport, indent=2, ensure_ascii=False) + "\n",
                                         encoding="utf-8", newline="\n")
print(f"measurements.csv v{VERSION}: {len(values)} строк, sha256 {passport['sha256'][:12]}")
