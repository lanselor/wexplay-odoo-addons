# -*- coding: utf-8 -*-

import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_sat_report_dms_file_id = fields.Many2one(
        comodel_name="dms.file",
        string="Informe SAT (DMS)",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    x_sat_report_notes = fields.Text(
        string="Notas complementarias del informe SAT",
        copy=False,
        help="Texto adicional incluido únicamente en el informe técnico SAT.",
    )

    def _check_sat_report_access(self, operation):
        """Authorize report actions without granting generic DMS access."""
        self.ensure_one()
        if operation not in ("download", "manage"):
            raise ValueError("Unsupported SAT report operation: %s" % operation)

        self.check_access("read")
        self.check_access_rule("read")
        user = self.env.user
        if self.env.is_superuser() or user.has_group("base.group_system"):
            return True

        group_xmlid = (
            "wexplay_repair.group_wex_repair_sat_report_manage"
            if operation == "manage"
            else "wexplay_repair.group_wex_repair_sat_report_download"
        )
        if not user.has_group(group_xmlid):
            raise AccessError(_("No tienes permiso para realizar esta acción sobre informes SAT."))
        return True

    # ── Hooks extensibles ──────────────────────────────────────────────────────
    # Cada módulo extensor sobreescribe el hook correspondiente.
    # La base devuelve lista vacía — las secciones condicionales del QWeb
    # no se renderizan si la lista está vacía.

    def _collect_sat_report_images(self):
        """Override en wexplay_repair_images para devolver imágenes marcadas."""
        self.ensure_one()
        return []

    def _collect_sat_report_consents(self):
        """Override en wex_consent para devolver consentimientos firmados."""
        self.ensure_one()
        return []

    # ── Helpers de etiquetas ──────────────────────────────────────────────────

    def _get_sat_report_selection_label(self, field_name, value):
        field = self._fields.get(field_name)
        if not field or not value:
            return ""
        return dict(field.selection).get(value, value)

    def _get_sat_report_budget_stage_label(self):
        self.ensure_one()
        budget_stage = getattr(self, "x_budget_stage", False)
        if not budget_stage:
            return ""
        field = self._fields.get("x_budget_stage")
        if not field:
            return ""
        return dict(field.selection).get(budget_stage, budget_stage)

    # ── Colectores de líneas ──────────────────────────────────────────────────

    def _get_sat_report_parts(self):
        self.ensure_one()
        parts = []
        for move in self.move_ids:
            if move.repair_line_type == "add" and move.state != "cancel":
                parts.append({
                    "product_name": move.product_id.display_name or "",
                    "qty_demand": move.product_uom_qty or 0.0,
                    "qty_done": move.quantity or 0.0,
                    "uom": move.product_uom.name or "",
                    "picked": move.picked,
                })
        return parts

    def _get_sat_report_services(self):
        self.ensure_one()
        if not self.sale_order_id:
            return []
        lines = []
        for line in self.sale_order_id.order_line:
            lines.append({
                "name": line.name or "",
                "qty": "%.2f" % line.product_uom_qty,
                "uom": line.product_uom.name or "",
            })
        return lines

    # ── Contexto principal para QWeb ──────────────────────────────────────────

    def _prepare_sat_report_context(self):
        self.ensure_one()
        images = self._collect_sat_report_images()
        consents = self._collect_sat_report_consents()

        # Una imagen por página conserva legibles capturas y detalles técnicos.
        image_pages = list(images)

        return {
            "repair": self,
            "company": self.company_id,
            "issuer_name": self.company_id.name,
            "issuer_logo": False,
            "issuer_primary_color": "#7b68b5",
            "generated_at": fields.Datetime.now(),
            # Cliente
            "partner": self.partner_id,
            "customer_reference": self.x_customer_reference or "",
            # Dispositivo
            "device_type_label": self._get_sat_report_selection_label(
                "x_device_type", self.x_device_type
            ),
            "brand": self.x_brand_id.name if self.x_brand_id else (self.x_brand or ""),
            "model": self.x_model_id.name if self.x_model_id else (self.x_model or ""),
            "imei": self.x_imei or "",
            "accessories": self.x_accessories or "",
            "unlock_type_label": self._get_sat_report_selection_label(
                "x_unlock_type", self.x_unlock_type
            ),
            # Diagnóstico
            "reported_issue": self.x_reported_issue or "",
            "internal_notes": self.internal_notes or "",
            "report_notes": self.x_sat_report_notes or "",
            # Trabajo realizado
            "parts": self._get_sat_report_parts(),
            "services": self._get_sat_report_services(),
            # Estado y responsables
            "budget_stage_label": self._get_sat_report_budget_stage_label(),
            "sat_priority_label": self._get_sat_report_selection_label(
                "x_sat_priority", self.x_sat_priority
            ),
            "responsible": self.user_id,
            "reception_employee": self.x_reception_employee_id,
            # Evidencia (pueden estar vacíos si los módulos no están instalados)
            "image_pages": image_pages,
            "consents": consents,
        }

    # ── DMS ───────────────────────────────────────────────────────────────────

    def _get_sat_report_dms_filename(self):
        self.ensure_one()
        return "informe-sat-%s.pdf" % self._get_sat_dms_safe_name()

    def _get_sat_report_dms_file(self):
        """Devuelve el archivo DMS existente del informe, o False."""
        self.ensure_one()
        if self.x_sat_report_dms_file_id and self.x_sat_report_dms_file_id.exists():
            return self.x_sat_report_dms_file_id
        # Fallback: buscar por nombre en DOCUMENTS por si el campo fue limpiado
        try:
            directory = self._get_or_create_sat_directory("DOCUMENTS")
        except Exception:
            return False
        filename = self._get_sat_report_dms_filename()
        found = self.env["dms.file"].search(
            [("directory_id", "=", directory.id), ("name", "=", filename)],
            limit=1,
        )
        return found or False

    def _save_sat_report_to_dms(self, pdf_bytes):
        self.ensure_one()
        directory = self._get_or_create_sat_directory("DOCUMENTS", create_defaults=True)
        filename = self._get_sat_report_dms_filename()
        content_b64 = base64.b64encode(pdf_bytes)
        existing = self.env["dms.file"].search(
            [("directory_id", "=", directory.id), ("name", "=", filename)],
            limit=1,
        )
        if existing:
            existing.write({"content": content_b64})
            dms_file = existing
        else:
            dms_file = self.env["dms.file"].create({
                "directory_id": directory.id,
                "name": filename,
                "content": content_b64,
            })
        self.write({"x_sat_report_dms_file_id": dms_file.id})
        return dms_file

    # ── Acciones ──────────────────────────────────────────────────────────────

    def _generate_sat_report_pdf(self, message_body):
        self.ensure_one()
        self._check_sat_report_access("manage")
        repair = self.sudo()
        report = repair.env.ref("wexplay_repair.action_report_sat_service")
        pdf_bytes, _fmt = repair.env["ir.actions.report"]._render_qweb_pdf(
            report.report_name,
            res_ids=repair.ids,
        )
        dms_file = repair._save_sat_report_to_dms(pdf_bytes)
        repair.message_post(
            body=message_body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return dms_file

    def _regenerate_sat_report_after_notes_update(self):
        """Keep the archived report synchronized when its note changes."""
        self.ensure_one()
        self._check_sat_report_access("manage")
        if not self.sudo()._get_sat_report_dms_file():
            return False

        self._generate_sat_report_pdf(
            _("Informe de servicio técnico actualizado con las notas complementarias.")
        )
        return True

    def action_open_sat_report_notes_wizard(self):
        self.ensure_one()
        self._check_sat_report_access("manage")
        wizard = self.env["wex.repair.sat.report.notes.wizard"].create({
            "repair_id": self.id,
            "notes": self.x_sat_report_notes,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Notas complementarias del informe"),
            "res_model": "wex.repair.sat.report.notes.wizard",
            "view_mode": "form",
            "view_id": self.env.ref(
                "wexplay_repair.view_wex_repair_sat_report_notes_wizard_form"
            ).id,
            "res_id": wizard.id,
            "target": "new",
        }

    def action_generate_sat_report(self):
        """Genera (o regenera) el informe SAT, lo guarda en DMS y lo descarga."""
        self.ensure_one()
        dms_file = self._generate_sat_report_pdf(
            _("Informe de servicio técnico generado y archivado en DMS.")
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/wexplay/repair/%s/sat-report/download" % self.id,
            "target": "self",
        }

    def action_download_sat_report(self):
        """Descarga el informe existente sin regenerarlo."""
        self.ensure_one()
        self._check_sat_report_access("download")
        dms_file = self.sudo()._get_sat_report_dms_file()
        if not dms_file:
            raise UserError(
                _("No hay informe generado para esta orden. Usa 'Generar informe' primero.")
            )
        return {
            "type": "ir.actions.act_url",
            "url": "/wexplay/repair/%s/sat-report/download" % self.id,
            "target": "self",
        }

    def _create_sat_report_mail_attachment(self, dms_file):
        """Create the temporary composer attachment from the archived DMS file."""
        self.ensure_one()
        return self.env["ir.attachment"].with_context(dms_file=True).create({
            "name": dms_file.name or self._get_sat_report_dms_filename(),
            "datas": dms_file.content,
            "mimetype": dms_file.mimetype or "application/pdf",
            "res_model": "mail.compose.message",
            "res_id": 0,
        })

    def action_send_sat_report(self):
        """Open Odoo's standard composer with the archived report attached."""
        self.ensure_one()
        self._check_sat_report_access("manage")
        dms_file = self.sudo()._get_sat_report_dms_file()
        if not dms_file:
            raise UserError(
                _("No hay informe generado para esta orden. Usa 'Generar informe' primero.")
            )

        attachment = self._create_sat_report_mail_attachment(dms_file)
        template = self.env.ref("wexplay_repair.mail_template_sat_service_report")
        return {
            "type": "ir.actions.act_window",
            "name": _("Enviar informe técnico"),
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "view_id": self.env.ref("mail.email_compose_message_wizard_form").id,
            "target": "new",
            "context": {
                "default_model": self._name,
                "default_res_ids": str(self.ids),
                "default_composition_mode": "comment",
                "default_template_id": template.id,
                "default_partner_ids": [(6, 0, self.partner_id.ids)],
                "default_attachment_ids": [(6, 0, attachment.ids)],
                "force_email": True,
            },
        }
