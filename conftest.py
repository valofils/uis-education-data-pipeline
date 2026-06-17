"""
conftest.py
Ensure the project root is on sys.path so pytest can import src.*
Location: conftest.py (project root)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
