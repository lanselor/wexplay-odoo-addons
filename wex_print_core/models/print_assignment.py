# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WexPrintAssignment(models.Model):
    _name = "wex.print.assignment"
    _description = "Wex Print Assignment"
    _order = "priority asc, id asc"

    name = fields.Char(string="Nombre", required=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(string="Prioridad", default=100)
    pilot_use_new_resolution = fields.Boolean(
        string="Activar resolución nueva",
        default=False,
        help="Permite que esta asignación active el camino nuevo en modo híbrido.",
    )

    document_type_id = fields.Many2one("wex.print.document.type", string="Tipo de documento", required=True, ondelete="cascade")
    report_action_id = fields.Many2one("ir.actions.report", string="Reporte (filtro)", ondelete="restrict")
    paperformat_id = fields.Many2one("report.paperformat", string="Formato de papel (filtro)", ondelete="restrict")
    profile_id = fields.Many2one("wex.print.profile", string="Perfil de impresión", required=True, ondelete="restrict")
    device_id = fields.Many2one(
        related="profile_id.device_id",
        string="Dispositivo",
        store=True,
        index=True,
        readonly=True,
    )
    document_report_action_id = fields.Many2one(
        related="document_type_id.report_action_id",
        string="Reporte del documento",
        readonly=True,
    )
    document_paperformat_id = fields.Many2one(
        related="document_type_id.paperformat_id",
        string="Formato del documento",
        readonly=True,
    )
    user_id = fields.Many2one("res.users", string="Usuario")
    company_id = fields.Many2one("res.company", string="Empresa")
    notes = fields.Text(string="Notas")

    @api.model_create_multi
    def create(self, values_list):
        assignments = super().create(values_list)
        assignments.mapped("device_id")._sync_capabilities_from_assignments()
        return assignments

    def write(self, values):
        previous_devices = self.mapped("device_id")
        result = super().write(values)
        (previous_devices | self.mapped("device_id"))._sync_capabilities_from_assignments()
        return result

    def unlink(self):
        devices = self.mapped("device_id")
        result = super().unlink()
        devices._sync_capabilities_from_assignments()
        return result

    def action_open_resolution_test(self):
        self.ensure_one()
        wizard = self.env["wex.print.resolution.test"].create({
            "assignment_id": self.id,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "wex.print.resolution.test",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.model
    def resolve_shadow(self, document_code, user_id=False, company_id=False):
        """Devuelve qué perfil nuevo habría aplicado el sistema en shadow mode."""
        document_type = self.env["wex.print.document.type"].search([("code", "=", document_code)], limit=1)
        if not document_type:
            return {
                "found": False,
                "document_code": document_code,
                "message": "Document type not found.",
            }

        user_id = user_id or self.env.user.id
        company_id = company_id or self.env.company.id

        candidates = self.search(
            [
                ("active", "=", True),
                ("document_type_id", "=", document_type.id),
                "|",
                ("report_action_id", "=", False),
                ("report_action_id.report_name", "=", document_type.get_report_name()),
                "|",
                ("paperformat_id", "=", False),
                ("paperformat_id", "=", document_type.paperformat_id.id),
                "|",
                ("user_id", "=", False),
                ("user_id", "=", user_id),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", company_id),
            ],
            order="priority asc, id asc",
        )

        best = False
        best_score = -1
        for candidate in candidates:
            score = 0
            if candidate.user_id:
                score += 20
            if candidate.company_id:
                score += 10
            if score > best_score:
                best = candidate
                best_score = score

        if not best:
            return {
                "found": False,
                "document_code": document_code,
                "document_type_id": document_type.id,
                "legacy_kind": document_type.legacy_kind,
                "message": "No shadow assignment matched.",
            }

        profile = best.profile_id
        printer_name = profile.get_resolved_printer_name()

        # Validación de compatibilidad: si el dispositivo tiene reportes declarados,
        # verificar que el reporte del documento está entre ellos. No bloqueante —
        # solo añade una advertencia al mensaje para que quede en el trace.
        compat_warning = ""
        device = profile.device_id
        if device and device.report_action_ids and document_type.report_action_id:
            compatible_ids = device.report_action_ids.ids
            if document_type.report_action_id.id not in compatible_ids:
                compat_warning = (
                    f" Warning: device '{device.name}' does not list report"
                    f" '{document_type.report_action_id.name}' as compatible."
                )

        return {
            "found": True,
            "document_code": document_code,
            "document_type_id": document_type.id,
            "assignment_id": best.id,
            "pilot_use_new_resolution": best.pilot_use_new_resolution,
            "profile_id": profile.id,
            "profile_name": profile.name,
            "device_id": device.id if device else False,
            "printer_name": printer_name,
            "allow_fallback": profile.allow_fallback,
            "legacy_kind": profile.legacy_kind or document_type.legacy_kind,
            "duplex_mode": profile.duplex_mode or "default",
            "message": "Shadow assignment resolved." + compat_warning,
        }
