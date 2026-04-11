"""
Pytest configuration.

This module adds the shared package to the Python path so it can be imported
during test collection and execution.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add shared package to Python path
# This allows importing app_shared during test collection
shared_path = Path(__file__).parent / "shared"
sys.path.insert(0, str(shared_path))


@pytest.fixture(autouse=True)
def mock_database_initialization(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Mock database initialization to prevent connection attempts during tests.

    This fixture automatically applies to all tests, mocking the init_db()
    function so that tests don't try to connect to a real database.
    """
    # Mock the init_db function from app_shared.database
    mock_init_db = MagicMock()
    monkeypatch.setattr("app_shared.database.init_db", mock_init_db)






