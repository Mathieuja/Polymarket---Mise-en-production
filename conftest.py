"""
Pytest configuration.

This module adds the shared package to the Python path so it can be imported
during test collection and execution.
"""

import sys
from pathlib import Path

# Add shared package to Python path
# This allows importing app_shared during test collection
shared_path = Path(__file__).parent / "shared"
sys.path.insert(0, str(shared_path))






