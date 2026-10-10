"""P4: время доставки и надёжность GitHub Pages и Helios по истории запусков GitHub Actions.

    python research/p4/timings.py            # обновить research/p4/data/runs.json и напечатать сводку

Публичный API без авторизации (60 запросов в час), поэтому ответы по завершённым запускам
кэшируются в runs.json и повторно не запрашиваются.

Что считается для каждого запуска workflow «Build and deploy» из push в main:
  * queue    — от создания запуска до старта job (ожидание раннера);
  * deliver  — сам шаг доставки: actions/deploy-pages или «Upload to Helios» (раньше tar по ssh);
  * total    — от push (создания запуска) до конца проверки опубликованного сайта.
"""

import json
import statistics
import urllib.request
from datetime import datetime
from pathlib import Path

API = "https://api.github.com/repos/crasavella04/python-lab3/actions"
CACHE = Path(__file__).resolve().parent / "data" / "runs.json"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "lab3-p4", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def secs(a, b):
    return (ts(b) - ts(a)).total_seconds() if a and b else None


def load():
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    runs = get(f"{API}/workflows/pages.yml/runs?per_page=100")["workflow_runs"]
    for run in runs:
        rid = str(run["id"])
        if rid in cache or run["status"] != "completed":
            continue
        jobs = get(f"{API}/runs/{rid}/jobs?per_page=50")["jobs"]
        cache[rid] = {
            "sha": run["head_sha"], "branch": run["head_branch"], "event": run["event"],
            "title": run["display_title"], "created_at": run["created_at"], "conclusion": run["conclusion"],
            "jobs": [{"name": j["name"], "conclusion": j["conclusion"], "started_at": j["started_at"],
                      "completed_at": j["completed_at"],
                      "steps": [{k: s[k] for k in ("name", "conclusion", "started_at", "completed_at")}
                                for s in j["steps"]]} for j in jobs],
        }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return cache


def step(job, *names):
    for s in job["steps"]:
        if any(n in s["name"] for n in names):
            return s
    return None


def measure(run):
    out = {}
    jobs = {j["name"]: j for j in run["jobs"]}
    build, dep, hel = jobs.get("build-pages"), jobs.get("deploy-pages"), jobs.get("deploy-helios")
    if dep and dep["conclusion"] == "success" and build:
        d = step(dep, "deploy-pages")
        v = step(dep, "Verify deployed site")
        out["pages"] = {"queue": secs(run["created_at"], build["started_at"]),
                        "deliver": secs(d["started_at"], d["completed_at"]) if d else None,
                        "total": secs(run["created_at"], (v or dep)["completed_at"])}
    if hel and hel["conclusion"] == "success":
        u = step(hel, "Upload to Helios")
        v = step(hel, "Healthcheck", "Verify deployed site")
        out["helios"] = {"queue": secs(run["created_at"], hel["started_at"]),
                         "deliver": secs(u["started_at"], u["completed_at"]) if u else None,
                         "total": secs(run["created_at"], (v or hel)["completed_at"])}
    return out


def summary(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return "—"
    return (f"медиана {statistics.median(values):.0f} с, min {values[0]:.0f}, max {values[-1]:.0f} "
            f"(n = {len(values)})")


def main():
    cache = load()
    runs = sorted(cache.values(), key=lambda r: r["created_at"])
    main_push = [r for r in runs if r["event"] == "push" and r["branch"] == "main"]
    print(f"Запусков в кэше: {len(runs)}, из них push в main: {len(main_push)}\n")
    for target in ("pages", "helios"):
        m = [measure(r).get(target) for r in main_push]
        m = [x for x in m if x]
        print(f"{target}:")
        for k in ("queue", "deliver", "total"):
            print(f"  {k:8} {summary(x[k] for x in m)}")

    print("\nНадёжность (все запуски, по job):")
    for name in ("build-pages", "deploy-pages", "deploy-helios"):
        concl = [j["conclusion"] for r in runs for j in r["jobs"] if j["name"] == name]
        counts = {c: concl.count(c) for c in sorted(set(concl), key=str)}
        print(f"  {name:14} {counts}")
        for r in runs:
            for j in r["jobs"]:
                if j["name"] == name and j["conclusion"] == "failure":
                    bad = next((s["name"] for s in j["steps"] if s["conclusion"] == "failure"), "?")
                    print(f"      {r['created_at'][:16]} {r['sha'][:7]} {r['branch']}: шаг «{bad}»")


if __name__ == "__main__":
    main()
