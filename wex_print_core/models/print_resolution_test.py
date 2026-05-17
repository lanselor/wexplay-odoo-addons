# -*- coding: utf-8 -*-
from odoo import fields, models


class WexPrintResolutionTest(models.TransientModel):
    _name = "wex.print.resolution.test"
    _description = "Simulador de resolución de impresión"

    # --- Entrada ---
    assignment_id = fields.Many2one("wex.print.assignment", string="Asignación", readonly=True)
    document_type_id = fields.Many2one(
        related="assignment_id.document_type_id",
        string="Tipo de documento",
        readonly=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        default=lambda self: self.env.user,
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
        required=True,
    )

    # --- Resultado ---
    simulated = fields.Boolean(default=False)
    result_found = fields.Boolean(string="Asignación encontrada", readonly=True)
    result_assignment_name = fields.Char(string="Asignación resuelta", readonly=True)
    result_profile_name = fields.Char(string="Perfil", readonly=True)
    result_device_name = fields.Char(string="Dispositivo", readonly=True)
    result_printer_name = fields.Char(string="Nombre en QZ", readonly=True)
    result_legacy_kind = fields.Char(string="Tipo", readonly=True)
    result_duplex_mode = fields.Char(string="Dúplex", readonly=True)
    result_allow_fallback = fields.Boolean(string="Fallback permitido", readonly=True)
    result_pilot = fields.Boolean(string="Resolución nueva activa", readonly=True)
    result_message = fields.Text(string="Mensaje del resolver", readonly=True)

    def action_simulate(self):
        self.ensure_one()
        doc_code = self.assignment_id.document_type_id.code
        resolution = self.env["wex.print.assignment"].resolve_shadow(
            doc_code,
            user_id=self.user_id.id,
            company_id=self.company_id.id,
        )

        profile = self.env["wex.print.profile"].browse(resolution.get("profile_id")) if resolution.get("profile_id") else False
        device = self.env["wex.print.device"].browse(resolution.get("device_id")) if resolution.get("device_id") else False
        assignment = self.env["wex.print.assignment"].browse(resolution.get("assignment_id")) if resolution.get("assignment_id") else False

        self.write({
            "simulated": True,
            "result_found": resolution.get("found", False),
            "result_assignment_name": assignment.name if assignment else "",
            "result_profile_name": profile.name if profile else "",
            "result_device_name": device.name if device else "",
            "result_printer_name": resolution.get("printer_name", ""),
            "result_legacy_kind": resolution.get("legacy_kind", ""),
            "result_duplex_mode": resolution.get("duplex_mode", ""),
            "result_allow_fallback": resolution.get("allow_fallback", False),
            "result_pilot": resolution.get("pilot_use_new_resolution", False),
            "result_message": resolution.get("message", ""),
        })

        # Reabrir el wizard con los resultados
        return {
            "type": "ir.actions.act_window",
            "res_model": "wex.print.resolution.test",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
