"""Связь опубликованного результата с версией кода и данных.

Манифест (manifest.json рядом с результатами) фиксирует:
  - code:   SHA-256 каждого файла кода эксперимента и общий хеш, коммит Git и признак незакоммиченных правок;
  - data:   версию датасета из паспорта data/DATASET.json и SHA-256 файла;
  - params: параметры запуска и их хеш;
  - env:    версии Python и ключевых пакетов;
  - outputs: SHA-256 каждого файла результата.

`python provenance.py check <каталог результатов>` пересчитывает хеши по текущему дереву и падает,
если код, параметры или данные изменились, а результаты не пересчитаны, либо если файлы результатов
правили вручную. Только стандартная библиотека: проверка идёт в CI без установки numpy и т.п.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE_FILES = ["experiment/coverage.py", "generate.py"]
DATASET_PASSPORT = "data/DATASET.json"


def sha256(path: Path) -> str:
    """Хеш с нормализацией переводов строк: одинаков на Windows и Linux."""
    data = path.read_bytes()
    if path.suffix in {".py", ".csv", ".md", ".json", ".svg"}:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def code_state() -> dict:
    files = {f: sha256(HERE / f) for f in CODE_FILES}
    return {"files": files, "sha256": sha256_json(files)}


def data_state() -> dict:
    passport = json.loads((HERE / DATASET_PASSPORT).read_text(encoding="utf-8"))
    actual = sha256(HERE / passport["file"])
    return {**passport, "sha256_actual": actual}


def git_state() -> dict:
    def git(*args):
        return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True).stdout.strip()
    paths = [str(HERE / f) for f in CODE_FILES] + [str(HERE / "data")]
    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain", "--", *paths))}


def check(results_dir: Path) -> int:
    manifest = json.loads((results_dir / "manifest.json").read_text(encoding="utf-8"))
    problems = []

    code = code_state()
    for f, h in code["files"].items():
        if manifest["code"]["files"].get(f) != h:
            problems.append(f"код изменён после расчёта: {f}")

    data = data_state()
    if data["sha256_actual"] != data["sha256"]:
        problems.append(f"файл данных не совпадает с паспортом {DATASET_PASSPORT} "
                        f"(данные изменили без новой версии датасета)")
    elif manifest["data"]["sha256"] != data["sha256_actual"]:
        problems.append(f"результаты посчитаны на другой версии данных: "
                        f"{manifest['data']['version']} → {data['version']}")

    if manifest["params_sha256"] != sha256_json(manifest["params"]):
        problems.append("параметры в манифесте не соответствуют их хешу")

    for name, h in manifest["outputs"].items():
        path = results_dir / name
        if not path.exists():
            problems.append(f"нет файла результата: {name}")
        elif sha256(path) != h:
            problems.append(f"файл результата изменён вручную: {name}")

    if manifest["git"]["dirty"]:
        problems.append("расчёт выполнен на незакоммиченном коде (git dirty)")

    print(f"Манифест: коммит {manifest['git']['commit'][:7]}, данные v{manifest['data']['version']}, "
          f"код {manifest['code']['sha256'][:12]}, запуск {manifest['run']['finished_utc']}")
    for p in problems:
        print("  FAIL", p)
    if not problems:
        print("  OK   результаты соответствуют текущему коду, параметрам и данным")
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "check":
        sys.exit(__doc__)
    sys.exit(check(Path(sys.argv[2])))
