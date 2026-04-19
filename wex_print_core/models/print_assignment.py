# -*- coding: utf-8 -*-
from odoo import api, fields, models


class WexPrintAssignment(models.Model):
    _name = "wex.print.assignment"
    _description = "Wex Print Assignment"
    _order = "priority asc, id asc"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(default=100)
    pilot_use_new_resolution = fields.Boolean(
        string="Pilot new resolution",
        default=False,
        help="Permite que esta asignacion active el camino nuevo en modo hibrido.",
    )

    document_type_id = fields.Many2one("wex.print.document.type", required=True, ondelete="cascade")
    profile_id = fields.Many2one("wex.print.profile", required=True, ondelete="restrict")
    user_id = fields.Many2one("res.users")
    company_id = fields.Many2one("res.company")
    notes = fields.Text()

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
        return {
            "found": True,
            "document_code": document_code,
            "document_type_id": document_type.id,
            "assignment_id": best.id,
            "pilot_use_new_resolution": best.pilot_use_new_resolution,
            "profile_id": profile.id,
            "profile_name": profile.name,
            "printer_name": profile.printer_name,
            "allow_fallback": profile.allow_fallback,
            "legacy_kind": profile.legacy_kind or document_type.legacy_kind,
            "duplex_mode": profile.duplex_mode or "default",
            "message": "Shadow assignment resolved.",
        }
