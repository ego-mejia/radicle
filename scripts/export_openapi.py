"""Write the OpenAPI document to frontend/openapi.json for the typed client.

Usage: cd backend && uv run python ../scripts/export_openapi.py
"""

import json
import sys
from pathlib import Path

from radicle.main import create_app

target = Path(__file__).resolve().parent.parent / "frontend" / "openapi.json"
target.write_text(json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n")
sys.stdout.write(f"wrote {target}\n")
