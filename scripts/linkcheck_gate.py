"""Решение по итогам `sphinx-build -b linkcheck`: падать только на битых ссылках.

    sphinx-build -q -b linkcheck docs _build/linkcheck || true
    python scripts/linkcheck_gate.py _build/linkcheck/output.json

Sphinx 9 завершается с кодом 1 и при битой ссылке, и при тайм-ауте. С облачных раннеров GitVerse
github.com и docs.selectel.ru иногда не отвечают за 20 с, и стадия lint блокировала выкладку,
хотя все ссылки рабочие. Здесь: broken → ошибка, timeout → предупреждение.
Нет output.json — значит, сама сборка не прошла; это тоже ошибка.
"""

import json
import sys
from collections import Counter
from pathlib import Path


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "_build/linkcheck/output.json")
    if not path.exists():
        print(f"::error title=linkcheck::нет {path} — linkcheck не отработал")
        sys.exit(1)
    results = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    counts = Counter(r["status"] for r in results)
    print("linkcheck: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for r in results:
        where = f"{r['filename']}:{r['lineno']}"
        if r["status"] == "broken":
            print(f"::error title=Битая ссылка::{where} {r['uri']} — {r['info']}")
        elif r["status"] == "timeout":
            print(f"::warning title=Тайм-аут ссылки::{where} {r['uri']} — сервер не ответил, проверить позже")
    sys.exit(1 if counts["broken"] else 0)


if __name__ == "__main__":
    main()
