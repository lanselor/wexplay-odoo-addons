import json
from pathlib import Path
assert env.cr.dbname == "codex_device_inspection_20261017"
meta=json.loads(Path("C:/odoo18/addons-wexplay/output/device_inspection_20261017/consent-ui-fixture.json").read_text())
doc=env["wex.consent.document"].browse(meta["document_id"])
assert doc.state == "pending_signature" and not doc.pdf_file
user=env["res.users"].search([("login", "=", "inspection_admin")], limit=1)
root=doc.repair_order_id._get_or_create_sat_root_directory()
group=env["dms.access.group"].create({"name": "Consent isolated test directory access", "perm_create": True, "perm_write": True, "explicit_user_ids": [(6,0,user.ids)]})
root.group_ids=[(4,group.id)]
env.cr.commit()
print("Isolated DMS directory access configured; request remains pending")
