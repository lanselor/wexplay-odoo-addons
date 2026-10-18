import json
from pathlib import Path
assert env.cr.dbname == "codex_device_inspection_20261017"
meta=json.loads(Path("C:/odoo18/addons-wexplay/output/device_inspection_20261017/consent-ui-fixture.json").read_text())
repair=env["repair.order"].browse(meta["repair_id"])
repair.partner_id.is_company=True
contact=env["res.partner"].create({"name":"Contacto portal ficticio", "parent_id":repair.partner_id.id})
user=env["res.users"].with_context(no_reset_password=True).create({
 "name":"Portal inspeccion - prueba", "login":"portal_inspection_preview",
 "password":"PortalInspectionLocal2026!", "partner_id":contact.id,
 "groups_id":[(6,0,env.ref("base.group_portal").ids)]})
foreign=env["repair.order"].create({"partner_id":env["res.partner"].create({"name":"Otra empresa ficticia","is_company":True}).id,
 "product_id":repair.product_id.id, "x_device_type":"mobile","x_device_description":"FOREIGN SECRET - NO PORTAL ACCESS"})
unsigned=env["repair.order"].create({"partner_id":repair.partner_id.id,"product_id":repair.product_id.id,
 "x_device_type":"laptop", "x_device_description":"Portatil gris registrado en recepcion.",
 "x_device_condition_ids":[(6,0,env.ref("wexplay_repair.device_condition_broken_screen").ids)],
 "x_device_inspection_marks":{"device_type":"laptop","front":[],"back":[[[0.7,0.7],[0.8,0.8]]]}})
values={"repair_id":repair.id,"foreign_id":foreign.id,"unsigned_id":unsigned.id}
Path("C:/odoo18/addons-wexplay/output/device_inspection_20261017/portal-ui-fixture.json").write_text(json.dumps(values))
env.cr.commit()
print(values)
