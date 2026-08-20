"""The stdio bridge must return clean JSON without an HTTP server."""

import json
import os
from pathlib import Path
import subprocess
import sys


def test_worker_handles_multiple_json_line_requests(tmp_path: Path) -> None:
    environment = {**os.environ, "PRISMA_DATA_ROOT": str(tmp_path)}
    worker = subprocess.Popen(
        [sys.executable, "-m", "src.worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=environment,
    )
    try:
        assert worker.stdin and worker.stdout
        worker.stdin.write(json.dumps({"id": 1, "method": "health", "params": {}}) + "\n")
        worker.stdin.write(json.dumps({"id": 2, "method": "auth.login", "params": {
            "login": "user", "password": "user1234"
        }}) + "\n")
        worker.stdin.flush()
        health = json.loads(worker.stdout.readline())
        login = json.loads(worker.stdout.readline())
        assert health["result"]["status"] == "ok"
        assert login["result"]["account"]["roles"] == ["USER"]
    finally:
        worker.terminate()
        worker.wait(timeout=10)
