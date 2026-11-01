"""Run with the Python bundled with Odoo (requires its libsass package)."""
from pathlib import Path

import sass

module = Path(__file__).resolve().parents[2]
source = module / "static/src/scss/repair_media_upload_dialog.scss"
css = sass.compile(filename=str(source))
assert "writing-mode: vertical-lr" in css
assert ".wex-pen-controls" in css
print("Odoo libsass: upload dialog styles compiled successfully")
