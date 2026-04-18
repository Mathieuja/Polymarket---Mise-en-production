"""Main entry point for the worker application."""

from __future__ import annotations

import asyncio
import os

if __package__ in {None, ""}:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from services.raw_ingestion_worker import main as run_raw_worker
    from services.transform_loader_worker import main as run_transform_worker
else:
    from .services.raw_ingestion_worker import main as run_raw_worker
    from .services.transform_loader_worker import main as run_transform_worker


def _resolve_worker_main():
    mode = os.getenv("WORKER_MODE", "raw").strip().lower()
    if mode == "transform":
        return run_transform_worker
    return run_raw_worker


def main() -> None:
    """Run the Polymarket ingestion worker."""

    asyncio.run(_resolve_worker_main()())


if __name__ == "__main__":
    main()
