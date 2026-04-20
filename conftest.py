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
def mock_database_initialization(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    """
    Mock database initialization to prevent connection attempts during tests.

    This fixture automatically applies to all tests, mocking the init_db()
    function so that tests don't try to connect to a real database.
    """
    # Only backend component tests need app initialization monkeypatching.
    if "tests/unit/components/backend" not in str(request.fspath):
        return

    # Mock the init_db function where it's used (in app.backend.api.main)
    # rather than where it's defined, since it's already imported.
    mock_init_db = MagicMock()
    try:
        monkeypatch.setattr("app.backend.api.main.init_db", mock_init_db)
    except ImportError:
        pytest.skip("Backend optional dependencies are not installed in this environment")






