import json
from pathlib import Path
assert env.cr.dbname == "codex_device_inspection_20261017"
user = env["res.users"].search([("login", "=", "inspection_admin")], limit=1)
assert user
user.groups_id = [(4, env.ref("wex_consent.group_wex_consent_manager").id)]
company = user.company_id
company.x_wex_consent_reception_legal_text = "SIMULACION INTERNA. Documento ficticio para probar la recepcion del dispositivo. Sin efectos contractuales."
if not company.x_wex_consent_dms_storage_id:
    company.x_wex_consent_dms_storage_id = env["dms.storage"].create({"name": "Consent isolated test storage", "save_type": "database", "company_id": company.id})
env["ir.config_parameter"].set_param("report.url", "http://127.0.0.1:8099")
env["ir.config_parameter"].set_param("wex_consent.auto_send_reception_email", "False")
env["ir.config_parameter"].set_param("wex_consent.auto_send_delivery_email", "False")
partner = env["res.partner"].create({"name": "Cliente ficticio - prueba de firmas"})
product = env["product.product"].create({"name": "Movil de prueba"})
repair = env["repair.order"].create({"partner_id": partner.id, "product_id": product.id,
    "company_id": company.id, "x_device_type": "mobile", "x_device_description": "Movil negro, 128 GB.\nGolpe en la esquina superior izquierda.",
    "x_reported_issue": "SIMULACION: el dispositivo no carga.",
    "x_device_condition_ids": [(6, 0, env.ref("wexplay_repair.device_condition_broken_screen").ids)],
    "x_device_inspection_marks": {"device_type": "mobile", "front": [[[0.15,0.18],[0.25,0.12],[0.35,0.18],[0.35,0.3],[0.25,0.36],[0.15,0.3],[0.15,0.18]]], "back": []}})
doc = env["wex.consent.document"].get_or_create_from_repair(repair, "reception")
doc.write({"signer_name": "Cliente ficticio", "signer_vat": "TEST-001"})
request = doc.action_request_signature()
metadata = {"repair_id": repair.id, "document_id": doc.id, "request_id": request.id,
    "action_id": env.ref("wex_consent.action_wex_consent_kiosk_client").id}
Path("C:/odoo18/addons-wexplay/output/device_inspection_20261017/consent-ui-fixture.json").write_text(json.dumps(metadata))
env.cr.commit()
print(metadata)
