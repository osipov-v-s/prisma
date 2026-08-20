"""Persistent JSON-lines worker connecting Electron IPC to Python services.

Only protocol responses go to stdout. Diagnostic logging goes to stderr so one
stray log line can never corrupt the request stream.
"""

import json
import logging
import sys
from typing import Any

from src.service.handlers import handle, initialize


logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="[prisma-worker] %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def main() -> None:
    # Make the protocol deterministic on Windows regardless of the active code page.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    initialize()
    LOGGER.info("worker ready")
    for line in sys.stdin:
        if not line.strip():
            continue
        response = _process(line)
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def _process(line: str) -> dict[str, Any]:
    request_id = None
    try:
        request = json.loads(line)
        request_id = request["id"]
        return {"id": request_id,
                "result": handle(request["method"], request.get("params", {}))}
    except Exception as error:
        LOGGER.exception("request failed")
        return {"id": request_id, "error": str(error) or error.__class__.__name__}


if __name__ == "__main__":
    main()
