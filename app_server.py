from __future__ import annotations

import json
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self) -> None:
        if self.path != "/run-solver":
            self.send_error(404, "Endpoint not found")
            return

        solver_path = ROOT / "main.py"
        if not solver_path.exists():
            self._send_json(
                404,
                {
                    "ok": False,
                    "message": "main.py not found in workspace root",
                    "stdout": "",
                    "stderr": "",
                    "returncode": None,
                },
            )
            return

        try:
            result = subprocess.run(
                [sys.executable, str(solver_path)],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            ok = result.returncode == 0
            self._send_json(
                200 if ok else 500,
                {
                    "ok": ok,
                    "message": "Solver executed successfully" if ok else "Solver exited with error",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                },
            )
        except subprocess.TimeoutExpired as exc:
            self._send_json(
                504,
                {
                    "ok": False,
                    "message": "Solver timed out after 60 seconds",
                    "stdout": exc.stdout or "",
                    "stderr": exc.stderr or "",
                    "returncode": None,
                },
            )
        except Exception as exc:
            self._send_json(
                500,
                {
                    "ok": False,
                    "message": f"Unexpected server error: {exc}",
                    "stdout": "",
                    "stderr": "",
                    "returncode": None,
                },
            )

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Server running at http://{host}:{port}")
    print("POST /run-solver to execute main.py")
    server.serve_forever()


if __name__ == "__main__":
    main()
