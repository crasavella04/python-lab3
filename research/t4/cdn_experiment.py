"""Сайт при недоступных CDN: варианты сборки и подмена адресов CDN.

    python research/t4/cdn_experiment.py build   # собрать варианты в research/t4/out
    python research/t4/cdn_experiment.py hang    # «зависший CDN» на 127.0.0.1:8899 (принимает и молчит)

Варианты:
  local         — как на сайте: KaTeX локально, font: false
  cdn           — «по умолчанию»: Roboto с Google Fonts, MathJax 3 с jsDelivr
  cdn-down      — cdn, но домены CDN не существуют (*.invalid): мгновенный отказ DNS
  cdn-hang      — cdn, но CDN принимает соединение и не отвечает (блокировка, перегрузка)
  local-down    — local, но и api.github.com (виджет репозитория) недоступен
"""

import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"
MKDOCS = ROOT / ".venv" / "Scripts" / "mkdocs.exe"
MATHJAX = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
CDN_HOSTS = ["fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net"]


def build(name: str, config_text: str) -> Path:
    cfg = ROOT / f"mkdocs-{name}.tmp.yml"
    cfg.write_text(config_text, encoding="utf-8")
    dest = OUT / name
    try:
        env = {**os.environ, "PYTHONUTF8": "1", "SITE_URL": "http://127.0.0.1:8810/"}
        subprocess.run([str(MKDOCS), "build", "-q", "-f", str(cfg), "-d", str(dest)],
                       cwd=ROOT, env=env, check=True)
    finally:
        cfg.unlink()
    return dest


def rewrite(src: Path, name: str, mapping: dict[str, str]) -> None:
    dest = OUT / name
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    for f in dest.rglob("*"):
        if f.suffix in {".html", ".js", ".css"}:
            text = f.read_text(encoding="utf-8")
            new = text
            for a, b in mapping.items():
                new = new.replace(a, b)
            if new != text:
                f.write_text(new, encoding="utf-8")


def cmd_build() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    base = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    local = build("local", base)

    cdn_cfg = base.replace("  font: false\n", "")
    cdn_cfg = re.sub(r"extra_javascript:\n(  - .*\n)+", f"extra_javascript:\n  - {MATHJAX}\n", cdn_cfg)
    cdn_cfg = re.sub(r"extra_css:\n(  - .*\n)+", "", cdn_cfg)
    assert "font: false" not in cdn_cfg and "katex" not in cdn_cfg
    cdn = build("cdn", cdn_cfg)

    rewrite(cdn, "cdn-down", {h: h.replace(".com", ".invalid").replace(".net", ".invalid") for h in CDN_HOSTS})
    rewrite(cdn, "cdn-hang", {f"https://{h}": "http://127.0.0.1:8899" for h in CDN_HOSTS})
    rewrite(local, "local-down", {"api.github.com": "api.github.invalid"})
    print("Собрано:", ", ".join(p.name for p in OUT.iterdir()))


def cmd_hang() -> None:
    """Принимает соединения и ничего не отвечает — как CDN за блокировкой или под нагрузкой."""
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 8899))
    srv.listen(100)
    held = []
    print("Зависший CDN слушает 127.0.0.1:8899")
    while True:
        conn, _ = srv.accept()
        held.append(conn)  # держим соединение открытым, не читаем и не отвечаем


if __name__ == "__main__":
    {"build": cmd_build, "hang": cmd_hang}[sys.argv[1]]()
