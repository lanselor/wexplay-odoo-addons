import json
from pathlib import Path
assert env.cr.dbname == "codex_device_inspection_20261017"
meta=json.loads(Path("C:/odoo18/addons-wexplay/output/device_inspection_20261017/consent-ui-fixture.json").read_text())
doc=env["wex.consent.document"].browse(meta["document_id"])
original=doc.snapshot_json
doc.repair_order_id.write({"x_device_description": "CAMBIO POSTERIOR: no debe llegar al cliente", "x_device_inspection_marks": False})
doc.action_refresh_from_repair()
assert doc.snapshot_json == original
assert len(doc._get_reception_inspection_snapshot()["views"]) == 2
env.cr.commit()
print("Pending snapshot unchanged after committed repair edits")
