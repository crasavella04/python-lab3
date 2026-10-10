"""Статический сервер с gzip — как GitHub Pages/Helios отдают текстовые файлы.

    python gzip_server.py PORT DIR

Без сжатия локальные файлы весили бы в разы больше CDN-ресурсов, которые приходят сжатыми,
и сравнение веса страниц было бы нечестным.
"""

import gzip
import http.server
import mimetypes
import os
import sys
from functools import partial
from urllib.parse import unquote, urlsplit

COMPRESS = {".html", ".css", ".js", ".mjs", ".json", ".svg", ".xml", ".txt", ".map"}


class GzipHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args, directory, **kwargs):
        self.root = os.path.abspath(directory)
        super().__init__(*args, **kwargs)

    def log_message(self, *args):
        pass

    def do_GET(self):
        url_path = unquote(urlsplit(self.path).path)
        path = os.path.abspath(os.path.join(self.root, url_path.lstrip("/")))
        if not path.startswith(self.root):
            return self.send_error(403)
        if os.path.isdir(path):
            if not url_path.endswith("/"):
                self.send_response(301)
                self.send_header("Location", url_path + "/")
                return self.end_headers()
            path = os.path.join(path, "index.html")
        if not os.path.isfile(path):
            return self.send_error(404)
        data = open(path, "rb").read()
        ext = os.path.splitext(path)[1].lower()
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ext in {".js", ".mjs", ".json", ".svg"}:
            ctype += "; charset=utf-8"
        gz = ext in COMPRESS and "gzip" in self.headers.get("Accept-Encoding", "")
        if gz:
            data = gzip.compress(data, 6)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=600")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    port, root = int(sys.argv[1]), sys.argv[2]
    http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(GzipHandler, directory=root)).serve_forever()
