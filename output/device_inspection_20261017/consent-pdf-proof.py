import base64
import io
import json
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw
assert env.cr.dbname == "codex_device_inspection_20261017"
out=Path("C:/odoo18/addons-wexplay/output/pdf")
meta=json.loads(Path("C:/odoo18/addons-wexplay/output/device_inspection_20261017/consent-ui-fixture.json").read_text())
user=env["res.users"].search([("login","=","inspection_admin")],limit=1)
doc=env["wex.consent.document"].browse(meta["document_id"])
assert doc.state == "signed" and doc.request_ids.state == "signed"
assert doc.device_description.startswith("Movil negro")
assert doc.repair_order_id.x_device_description.startswith("CAMBIO POSTERIOR")
assert base64.b64decode(doc.pdf_file) == base64.b64decode(doc.dms_file_id.content)
assert doc.dms_file_id.directory_id.name == "SIGNATURES"
(out/"consent-reception-mobile.pdf").write_bytes(base64.b64decode(doc.pdf_file))
print("Browser signature + frozen snapshot + DMS OK")
image=Image.new("RGB",(300,100),"white")
draw=ImageDraw.Draw(image)
draw.line([(30,70),(90,20),(130,80),(200,30),(260,60)], fill="black",width=3)
buffer=io.BytesIO()
image.save(buffer,format="PNG")
signature=base64.b64encode(buffer.getvalue()).decode()
scenarios=[
 ("consent-reception-console","reception","console","handheld_pc","Consola de prueba entregada con marcas en ambas caras.",True),
 ("consent-reception-long","reception","laptop",None,"Descripcion extensa de prueba. Estado de recepcion sin recortes.\n"*85,True),
 ("consent-reception-empty","reception","mobile",None,"",False),
 ("consent-delivery","delivery","mobile",None,"Descripcion de entrega de prueba.",False),
]
for filename,kind,device_type,console_format,description,has_marks in scenarios:
 repair=env["repair.order"].create({"partner_id":doc.partner_id.id,"product_id":doc.repair_order_id.product_id.id,
  "company_id":doc.company_id.id,"x_device_type":device_type,"x_device_description":description,
  "x_reported_issue":"SIMULACION - documento sin efectos contractuales", "internal_notes":"Revision de prueba realizada."})
 if has_marks:
  marks={"device_type":device_type,"front":[[[0.1,0.2],[0.3,0.4]]],"back":[[[0.6,0.7],[0.8,0.9]]]}
  if console_format: marks["console_format"]=console_format
  repair.write({"x_device_inspection_marks":marks,"x_device_condition_ids":[(6,0,env.ref("wexplay_repair.device_condition_broken_screen").ids)]})
 document=env["wex.consent.document"].get_or_create_from_repair(repair,kind).with_user(user)
 request=document.action_request_signature()
 session=env["wex.consent.kiosk.session"].with_user(user).get_default_session(doc.company_id.id)
 request.action_mark_presented(session)
 original=document.snapshot_json
 repair.x_device_description="EDITADO DESPUES DE SOLICITAR"
 with patch.object(type(repair),"_prepare_device_inspection_snapshot", side_effect=AssertionError("live inspection read")):
  request.action_sign_request("Firmante ficticio",signature,confirmation_ok=True,signer_vat="TEST-001",consent_values={"legal_data_protection":True,"warranty_conditions_accepted":True})
 assert document.snapshot_json == original
 assert base64.b64decode(document.pdf_file) == base64.b64decode(document.dms_file_id.content)
 assert document.state == "signed" and request.state == "signed"
 (out/(filename+".pdf")).write_bytes(base64.b64decode(document.pdf_file))
 print("Signed PDF + DMS OK:",filename)
env.cr.rollback()
