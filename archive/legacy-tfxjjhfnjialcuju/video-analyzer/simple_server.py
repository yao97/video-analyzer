from http.server import HTTPServer, SimpleHTTPRequestHandler, ThreadingHTTPServer
import os, sys

PORT = 8765
DIR = r"C:\Users\EDY\.qclaw\workspace-tfxjjhfnjialcuju\video-analyzer"

class Handler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'  # 关闭 keep-alive，避免单连接长期占用

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
print(f'Serving at http://127.0.0.1:{PORT}/web_player_v3.html')
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 1))
    ip = s.getsockname()[0]
    print(f'LAN access: http://{ip}:{PORT}/web_player_v3.html')
except Exception:
    pass
finally:
    s.close() if 's' in dir() else None
sys.stdout.flush()
server.serve_forever()
