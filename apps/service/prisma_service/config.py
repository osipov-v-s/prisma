"""Configuration of the local prototype service."""

import os
from pathlib import Path

from prisma.persistence.database import DATA_ROOT

SERVICE_NAME = "ПРИЗМА Application Service"
SERVICE_VERSION = "1.0.0"
API_PREFIX = "/api/v1"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
COLLECTION_STORAGE_ROOT = Path(os.getenv("PRISMA_DATA_ROOT", DATA_ROOT)) / "collections"
