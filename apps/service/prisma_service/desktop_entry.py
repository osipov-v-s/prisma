"""Executable entry point bundled next to Electron for Windows Desktop."""

import uvicorn
from apps.service.prisma_service.main import app


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")
