# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_warranty_repair_count = fields.Integer(
        string="Número de garantías",
        compute="_compute_x_warranty_repair_count",
    )

    @api.depends("child_ids")
    def _compute_x_warranty_repair_count(self):
        repair_model = self.env["repair.order"]
        for partner in self:
            partner.x_warranty_repair_count = repair_model.search_count(
                [
                    ("partner_id", "child_of", partner.id),
                    ("x_is_warranty_case", "=", True),
                ]
            )

    def action_view_warranty_repairs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Garantías SAT"),
            "res_model": "repair.order",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "child_of", self.id),
                ("x_is_warranty_case", "=", True),
            ],
            "context": {
                "search_default_warranty_cases": 1,
                "default_partner_id": self.id,
            },
        }
