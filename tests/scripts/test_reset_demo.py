import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from scripts.demo.reset_demo import preview_seed, reset_demo


def test_seed_preview_returns_a_fresh_state_without_modifying_the_source_seed():
    seed_path = Path("data/scenarios/lunch-rush.json")
    source_before = seed_path.read_bytes()

    first_state = preview_seed(seed_path)
    first_state["customer"]["name"] = "Changed in memory"
    second_state = preview_seed(seed_path)

    assert second_state["customer"]["name"] == "Demo Customer"
    assert second_state is not first_state
    assert second_state["customer"] is not first_state["customer"]
    assert seed_path.read_bytes() == source_before


def test_reset_demo_posts_to_the_running_api():
    requests = []

    class ResetHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append((self.command, self.path))
            body = json.dumps({"scenario_id": "lunch-rush", "clock_minutes": 0}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), ResetHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        state = reset_demo(f"http://127.0.0.1:{server.server_port}")
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert state["scenario_id"] == "lunch-rush"
    assert requests == [("POST", "/api/v1/demo/reset")]
