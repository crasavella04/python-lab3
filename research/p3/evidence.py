"""Доказательства для отчёта P3: что показывают CI и развёрнутые сайты.

    python research/p3/evidence.py [RUN_ID ...]   # без аргументов — последний запуск

Для запуска GitHub Actions (публичный API, без авторизации): длительность шагов кэша и сборки.
Для обоих сайтов: метка версии и строка «Расчёт: …» со страницы P3, строка таблицы режима C.
"""

import json
import re
import sys
import urllib.request
from datetime import datetime

API = "https://api.github.com/repos/crasavella04/python-lab3/actions"
SITES = {"GitHub Pages": "https://crasavella04.github.io/python-lab3/p3/",
         "Helios": "https://se.ifmo.ru/~s564180/python-lab3/p3/"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "lab3-evidence"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def dur(step):
    if not step.get("started_at") or not step.get("completed_at"):
        return None
    t = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (t(step["completed_at"]) - t(step["started_at"])).total_seconds()


def run_info(run_id):
    run = json.loads(get(f"{API}/runs/{run_id}"))
    print(f"Запуск {run_id}: коммит {run['head_sha'][:7]} «{run['display_title'][:60]}» — "
          f"{run['status']} {run['conclusion'] or ''}")
    for job in json.loads(get(f"{API}/runs/{run_id}/jobs"))["jobs"]:
        steps = [s for s in job["steps"] if "P3" in s["name"] or "Build site" in s["name"]]
        print(f"  {job['name']}: {job['conclusion'] or job['status']}; " +
              "; ".join(f"{s['name'][:40]} — {dur(s)} с" for s in steps))


def site_info():
    for name, url in SITES.items():
        try:
            html = get(url)
        except Exception as e:  # noqa: BLE001
            print(f"  {name}: {e}")
            continue
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        version = re.search(r"Набор данных версия ([\d.]+), (\d+) измерений", text)
        calc = re.search(r"Расчёт (.+?) с \(ключ кэша ([0-9a-f]+)\)", text)
        commit = re.search(r'build-marker" content="python-lab3:([0-9a-f]+|local)', html)
        row_c = re.search(r"\| C \| .*?\|", text) or re.search(r"C (\d+) ([\d.]+) ([\d.]+) – ([\d.]+)", text)
        print(f"  {name}: коммит {commit.group(1)[:7] if commit else '?'}, "
              f"данные v{version.group(1) if version else '?'} ({version.group(2) if version else '?'} изм.), "
              f"расчёт: {calc.group(1) + ' с, ключ ' + calc.group(2) if calc else '?'}, "
              f"режим C: n={row_c.group(1)}, среднее {row_c.group(2)} мс" if row_c and row_c.lastindex else "")


if __name__ == "__main__":
    ids = sys.argv[1:] or [json.loads(get(f"{API}/runs?per_page=1"))["workflow_runs"][0]["id"]]
    for i in ids:
        run_info(i)
    print("Сайты:")
    site_info()
