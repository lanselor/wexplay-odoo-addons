import base64
import io
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw

out = Path("C:/odoo18/addons-wexplay/output/pdf")
out.mkdir(parents=True, exist_ok=True)
env["ir.config_parameter"].sudo().set_param("report.url", "http://127.0.0.1:8098")
partner = env["res.partner"].create({"name": "Cliente de prueba - Informe SAT"})
product = env["product.product"].create({"name": "Dispositivo de prueba"})
repair = env["repair.order"].create({"partner_id": partner.id, "product_id": product.id,
    "x_device_type": "mobile", "x_reported_issue": "El dispositivo no enciende.",
    "internal_notes": "Se realiza comprobacion del estado y diagnostico inicial."})
company = repair.company_id
if not company.x_wex_consent_dms_storage_id:
    company.x_wex_consent_dms_storage_id = env["dms.storage"].create({
        "name": "Inspection report isolated storage", "save_type": "database",
        "company_id": company.id,
    })
photo = Image.new("RGB", (1000, 650), "#e9edf4")
draw = ImageDraw.Draw(photo)
draw.rounded_rectangle((350, 50, 650, 600), radius=40, outline="#383838", width=12)
draw.text((60, 50), "FOTOGRAFIA DE PRUEBA - SAT", fill="#383838")
buffer = io.BytesIO()
photo.save(buffer, format="PNG")
photos = [{"name": "Fotografia de prueba", "src": "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(),
           "description": "Evidencia fotografica posterior al estado de recepcion.", "tags": "Prueba"}]
front = [[[0.2,0.2],[0.3,0.15],[0.4,0.2],[0.4,0.3],[0.3,0.35],[0.2,0.3],[0.2,0.2]]]
back = [[[0.65,0.7],[0.75,0.65],[0.85,0.7],[0.85,0.8],[0.75,0.85],[0.65,0.8],[0.65,0.7]]]
condition = env.ref("wexplay_repair.device_condition_broken_screen")
report = env.ref("wexplay_repair.action_report_sat_service")
scenarios = [
    ("inspection-mobile", "mobile", None, front, [], "Dispositivo negro, 128 GB.\nGolpe en la esquina superior izquierda.", True),
    ("inspection-console", "console", "desktop", front, back, "Consola blanca entregada sin mando.", True),
    ("inspection-laptop", "laptop", None, [], back, "Portatil gris. Marcas en la base.", True),
    ("inspection-long-text", "tablet", None, front, [], "Descripcion extensa de prueba. Texto completo sin recortes.\n" * 90, True),
    ("inspection-tags-only", "monitor", None, [], [], "", True),
    ("inspection-empty", "mobile", None, [], [], "", False),
]
with patch.object(type(repair), "_collect_sat_report_images", lambda self: photos):
    for filename, device_type, console_format, front_marks, back_marks, description, tags in scenarios:
        marks = {"device_type": device_type, "front": front_marks, "back": back_marks}
        if console_format:
            marks["console_format"] = console_format
        repair.write({"x_device_type": device_type, "x_device_description": description,
            "x_device_condition_ids": [(6,0,condition.ids if tags else [])],
            "x_device_inspection_marks": marks if (front_marks or back_marks or console_format) else False})
        pdf, _ = env["ir.actions.report"]._render_qweb_pdf(report.report_name, res_ids=repair.ids)
        saved = repair._save_sat_report_to_dms(pdf)
        assert base64.b64decode(saved.content) == pdf
        assert saved == repair.x_sat_report_dms_file_id
        (out / (filename + ".pdf")).write_bytes(pdf)
        print("PDF + DMS OK:", filename, len(pdf))
# Roll back all test records/settings; proof files remain outside the database.
env.cr.rollback()
