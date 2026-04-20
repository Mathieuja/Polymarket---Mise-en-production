"""Versioned database migrations for the shared PostgreSQL schema."""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from typing import Callable

from sqlalchemy import text
from sqlalchemy.engine import Engine

MIGRATION_TABLE = "schema_migrations"
MIGRATION_LOCK_KEY = 847392114


@dataclass(frozen=True)
class Migration:
    """Single versioned database migration."""

    version: str
    upgrade: Callable[[object], None]


def _load_migrations() -> list[Migration]:
    package_name = f"{__name__}.versions"
    package = importlib.import_module(package_name)

    migrations: list[Migration] = []
    for module_info in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_info.name}")
        version = getattr(module, "version", None)
        upgrade = getattr(module, "upgrade", None)
        if not version or not callable(upgrade):
            continue
        migrations.append(Migration(version=version, upgrade=upgrade))

    migrations.sort(key=lambda migration: migration.version)
    return migrations


def run_migrations(engine: Engine) -> None:
    """Apply all pending migrations in order."""

    migrations = _load_migrations()
    if not migrations:
        return

    with engine.begin() as connection:
        # Ensure only one process applies migrations at a time.
        if engine.dialect.name == "postgresql":
            connection.execute(text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": MIGRATION_LOCK_KEY})

        connection.execute(
            text(
                f'CREATE TABLE IF NOT EXISTS "{MIGRATION_TABLE}" ('
                'version VARCHAR(128) PRIMARY KEY, '
                'applied_at TIMESTAMP NOT NULL DEFAULT NOW()'
                ')'
            )
        )

        applied_versions = {
            row[0]
            for row in connection.execute(
                text(f'SELECT version FROM "{MIGRATION_TABLE}"')
            )
        }

        for migration in migrations:
            if migration.version in applied_versions:
                continue

            migration.upgrade(connection)
            if engine.dialect.name == "postgresql":
                connection.execute(
                    text(
                        f'INSERT INTO "{MIGRATION_TABLE}" (version) VALUES (:version) '
                        'ON CONFLICT (version) DO NOTHING'
                    ),
                    {"version": migration.version},
                )
            else:
                connection.execute(
                    text(f'INSERT INTO "{MIGRATION_TABLE}" (version) VALUES (:version)'),
                    {"version": migration.version},
                )
