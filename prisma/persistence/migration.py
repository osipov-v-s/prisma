"""Run Alembic migrations before the local service accepts requests."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from .database import PROJECT_ROOT


def upgrade_database() -> None:
    config_path = Path(PROJECT_ROOT, "alembic.ini")
    config = Config(str(config_path))
    config.set_main_option("script_location", str(Path(PROJECT_ROOT, "migrations")))
    command.upgrade(config, "head")
