# -*- coding: utf-8 -*-

import base64
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import formatLang

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

    # ── Formateo monetario ────────────────────────────────────────────────────

    def _fmt_monetary(self, amount, currency):
        return formatLang(self.env, amount, currency_obj=currency)

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
            currency = line.currency_id
            lines.append({
                "name": line.name or "",
                "qty": "%.2f" % line.product_uom_qty,
                "uom": line.product_uom.name or "",
                "price_unit_fmt": self._fmt_monetary(line.price_unit, currency),
                "price_subtotal_fmt": self._fmt_monetary(line.price_subtotal, currency),
            })
        return lines

    # ── Contexto principal para QWeb ──────────────────────────────────────────

    def _prepare_sat_report_context(self):
        self.ensure_one()
        sale = self.sale_order_id
        images = self._collect_sat_report_images()
        consents = self._collect_sat_report_consents()

        # Agrupar imágenes en pares para el grid de 2 columnas
        image_pairs = [images[i:i + 2] for i in range(0, len(images), 2)]

        return {
            "repair": self,
            "company": self.company_id,
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
            # Económico (importes pre-formateados en Python)
            "has_sale": bool(sale),
            "amount_untaxed_fmt": self._fmt_monetary(
                sale.amount_untaxed if sale else 0.0,
                sale.currency_id if sale else self.company_id.currency_id,
            ),
            "amount_tax_fmt": self._fmt_monetary(
                sale.amount_tax if sale else 0.0,
                sale.currency_id if sale else self.company_id.currency_id,
            ),
            "amount_total_fmt": self._fmt_monetary(
                sale.amount_total if sale else 0.0,
                sale.currency_id if sale else self.company_id.currency_id,
            ),
            # Evidencia (pueden estar vacíos si los módulos no están instalados)
            "image_pairs": image_pairs,
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

    def action_generate_sat_report(self):
        """Genera (o regenera) el informe SAT, lo guarda en DMS y lo descarga."""
        self.ensure_one()
        report = self.env.ref("wexplay_repair.action_report_sat_service")
        pdf_bytes, _fmt = self.env["ir.actions.report"]._render_qweb_pdf(
            report.report_name,
            res_ids=self.ids,
        )
        dms_file = self._save_sat_report_to_dms(pdf_bytes)
        self.message_post(
            body=_("Informe de servicio técnico generado y archivado en DMS."),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/dms.file/%s/content/%s?download=true"
            % (dms_file.id, self._get_sat_report_dms_filename()),
            "target": "self",
        }

    def action_download_sat_report(self):
        """Descarga el informe existente sin regenerarlo."""
        self.ensure_one()
        dms_file = self._get_sat_report_dms_file()
        if not dms_file:
            raise UserError(
                _("No hay informe generado para esta orden. Usa 'Generar informe' primero.")
            )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/dms.file/%s/content/%s?download=true"
            % (dms_file.id, self._get_sat_report_dms_filename()),
            "target": "self",
        }
