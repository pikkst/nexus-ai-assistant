"""
Nexus Face — HTTP API server for the animated face.

Serves SVG frames over HTTP so the animated demo HTML can talk to it.

Run:  python src/ui/face_server.py
Then open: http://localhost:8765/face-demo
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Make imports work regardless of how we're run
_script_dir = pathlib.Path(__file__).resolve().parent
_src_dir = _script_dir.parent  # src/
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from ui.face import NexusFace, Emotion

HERE = _script_dir
face_instance = NexusFace()


class FaceHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")

        if path == "/api/face/render":
            emotion = params.get("emotion", ["idle"])[0]
            try:
                svg = face_instance.render(emotion)
            except ValueError:
                svg = face_instance.render("idle")
            self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            self.end_headers()
            self.wfile.write(svg.encode("utf-8"))

        elif path == "/api/face/animate":
            emotion = params.get("emotion", ["idle"])[0]
            try:
                face_instance.state.emotion = Emotion(emotion)
            except ValueError:
                face_instance.state.emotion = Emotion.IDLE
            svg = face_instance.animate(dt=0.05)
            self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            self.end_headers()
            self.wfile.write(svg.encode("utf-8"))

        elif path == "/api/face/emotions":
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            emotions = [e.value for e in Emotion]
            self.wfile.write(json.dumps({"emotions": emotions}).encode("utf-8"))

        elif path == "/api/face/config":
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            cfg = face_instance.config
            self.wfile.write(json.dumps({
                "width": cfg.width, "height": cfg.height,
                "bg_color": cfg.bg_color, "head_color": cfg.head_color,
            }).encode("utf-8"))

        elif path in ("/face-demo", "/", "/index.html"):
            demo_path = HERE / "face_demo_animated.html"
            if demo_path.exists():
                html = demo_path.read_text(encoding="utf-8")
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            else:
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Demo file not found. Run: python src/ui/face.py")

        elif path == "/face-grid":
            grid_path = HERE / "face_demo_grid.html"
            if grid_path.exists():
                html = grid_path.read_text(encoding="utf-8")
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html.encode("utf-8"))
            else:
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Grid file not found.")

        elif path == "/api/face/state":
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            s = face_instance.state
            self.wfile.write(json.dumps({
                "emotion": s.emotion.value, "blink": s.blink.value,
                "blink_timer": s.blink_timer, "gaze_x": round(s.gaze_x, 3),
                "gaze_y": round(s.gaze_y, 3), "mouth_open": round(s.mouth_open, 3),
                "eye_scale": round(s.eye_scale, 3), "time": round(s.time, 3),
            }).encode("utf-8"))

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found. Try /face-demo or /api/face/render?emotion=idle")

    def log_message(self, format: str, *args) -> None:
        if "favicon" not in str(args[0]):
            super().log_message(format, *args)


def main() -> None:
    port = int(os.environ.get("NEXUS_FACE_PORT", "8765"))
    server = HTTPServer(("0.0.0.0", port), FaceHandler)
    print(f"[nexus.face] Face server running at http://localhost:{port}/face-demo")
    print(f"[nexus.face] Emotion grid at http://localhost:{port}/face-grid")
    print(f"[nexus.face] API: GET /api/face/render?emotion=happy")
    print(f"[nexus.face] Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[nexus.face] Server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
