"""Loopback-only map document server, with an unguessable URL and no file access."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import secrets
import mimetypes

class MapServer:
    def __init__(self):
        self.page = Path(__file__).with_name('map.html').read_bytes()
        self.path = '/' + secrets.token_urlsafe(24) + '/'
        base = Path(__file__).parent / 'vendor' / 'leaflet-1.9.4'
        self.assets = {}
        for name in ('leaflet.js', 'leaflet.css', 'images/layers.png', 'images/layers-2x.png',
                     'images/marker-icon.png', 'images/marker-icon-2x.png', 'images/marker-shadow.png'):
            self.assets[self.path + 'vendor/' + name] = (
                (base / name).read_bytes(), mimetypes.guess_type(name)[0] or 'application/octet-stream')
        fonts = Path(__file__).parent / 'assets' / 'fonts' / 'nanum-gothic'
        for weight in ('Regular', 'Bold'):
            name = f'NanumGothic-{weight}.ttf'
            self.assets[self.path + 'fonts/' + name] = ((fonts / name).read_bytes(), 'font/ttf')
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == owner.path:
                    body, content_type, cache = owner.page, 'text/html; charset=utf-8', 'no-store'
                elif self.path in owner.assets:
                    body, content_type = owner.assets[self.path]
                    cache = 'public, max-age=31536000, immutable'
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Cache-Control', cache)
                self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        # Let the OS choose a unique port. On Windows, reuse-address can allow
        # multiple instances on a fixed port and route a page to the wrong app.
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_port}{self.path}'
        Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
