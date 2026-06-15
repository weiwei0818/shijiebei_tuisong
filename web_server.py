"""
Simple HTTP server serving the web/ directory for mobile phone access.
Runs on port 8888 by default.
"""
import os
import sys
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(PROJECT_DIR, "web")
DEFAULT_PORT = 8888


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """Handler with CORS headers for local network access."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def get_local_ip() -> str:
    """Get local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    os.makedirs(WEB_DIR, exist_ok=True)

    ip = get_local_ip()
    server = HTTPServer(("0.0.0.0", port), CORSRequestHandler)

    print(f"  ⚽ 世界杯播报服务已启动")
    print(f"  本地访问: http://127.0.0.1:{port}")
    print(f"  手机访问: http://{ip}:{port}")
    print(f"  按 Ctrl+C 停止服务")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  服务已停止")
        server.server_close()


if __name__ == "__main__":
    main()
