"""Сводка отчётов Lighthouse (P2) и извлечение скриншотов.

    python parse_lighthouse.py   # → lighthouse_summary.json, docs/p2/*.jpg
"""

import base64
import json
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image

HERE = Path(__file__).resolve().parent
IMG = HERE.parent.parent / "docs" / "p2"
IMG.mkdir(parents=True, exist_ok=True)
LOCAL = "127.0.0.1"
# Антивирус на машине замера внедряет в каждую страницу свой скрипт — это не запрос генератора
ENV_NOISE = ("kaspersky-labs.com",)


def save_jpeg(data_uri: str, path: Path, width: int | None = None):
    img = Image.open(BytesIO(base64.b64decode(data_uri.split(",", 1)[1]))).convert("RGB")
    if width and img.width > width:
        img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    img.save(path, "JPEG", quality=78, optimize=True)
    return img.size


def main():
    summary = {}
    for f in sorted((HERE / "lighthouse").glob("*.json")):
        gen, mode = f.stem.rsplit("-", 1)
        r = json.loads(f.read_text(encoding="utf-8"))
        a = r["audits"]
        all_reqs = [x for x in a["network-requests"]["details"]["items"] if x["url"].startswith("http")]
        noise = [x for x in all_reqs if (urlsplit(x["url"]).hostname or "").endswith(ENV_NOISE)]
        reqs = [x for x in all_reqs if x not in noise]
        ext = [x for x in reqs if urlsplit(x["url"]).hostname != LOCAL]
        row = {
            "scores": {k: round(v["score"] * 100) for k, v in r["categories"].items()},
            "total_kb": round(sum(x.get("transferSize", 0) for x in reqs) / 1024),
            "noise_kb": round(sum(x.get("transferSize", 0) for x in noise) / 1024),
            "requests": len(reqs),
            "external_requests": len(ext),
            "external_kb": round(sum(x.get("transferSize", 0) for x in ext) / 1024),
            "external_hosts": sorted({urlsplit(x["url"]).hostname for x in ext}),
            "fcp_s": round(a["first-contentful-paint"]["numericValue"] / 1000, 2),
            "lcp_s": round(a["largest-contentful-paint"]["numericValue"] / 1000, 2),
            "tbt_ms": round(a["total-blocking-time"]["numericValue"]),
            "cls": round(a["cumulative-layout-shift"]["numericValue"], 3),
            # content-width в Lighthouse 13 удалён; горизонтальная прокрутка проверяется отдельно в браузере
            "meta_viewport_ok": a["meta-viewport"]["score"] == 1,
            "viewport_insight_ok": a["viewport-insight"].get("score") in (1, None),
            "failed_a11y": [k for k, v in a.items() if v.get("score") == 0 and k in {
                ref["id"] for ref in r["categories"]["accessibility"]["auditRefs"]}],
            "failed_bp": [k for k, v in a.items() if v.get("score") == 0 and k in {
                ref["id"] for ref in r["categories"]["best-practices"]["auditRefs"]}],
        }
        shot = a["final-screenshot"]["details"]["data"]
        row["screenshot"] = f"{gen}-{mode}.jpg"
        save_jpeg(shot, IMG / row["screenshot"])
        if mode == "mobile":
            full = r.get("fullPageScreenshot", {}).get("screenshot", {}).get("data")  # в Lighthouse 13 — в корне отчёта
            if full:
                row["fullpage"] = f"{gen}-mobile-full.jpg"
                row["fullpage_size"] = save_jpeg(full, IMG / row["fullpage"], width=360)
        summary.setdefault(gen, {})[mode] = row
        print(f"{gen:12} {mode:8} {row['scores']} {row['total_kb']} КБ, запросов {row['requests']} "
              f"(внешних {row['external_requests']}: {', '.join(row['external_hosts'])}), "
              f"meta-viewport {'OK' if row['meta_viewport_ok'] else 'FAIL'}")
    (HERE / "lighthouse_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
