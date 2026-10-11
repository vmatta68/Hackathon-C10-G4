
"""Ensure pytest can import the project's src package."""

import sys
from pathlib import Path

# tests/conftest.py -> parent directory is the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
project_root_text = str(PROJECT_ROOT)

if project_root_text not in sys.path:
    sys.path.insert(0, project_root_text)
