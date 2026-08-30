# -*- coding: utf-8 -*-

from odoo import _, fields, models


class RepairWarrantyClaimWizard(models.TransientModel):
    _name = "wex.repair.warranty.claim.wizard"
    _description = "Asistente de tramitación de garantía"

    repair_id = fields.Many2one(
        "repair.order",
        string="SAT",
        required=True,
        readonly=True,
    )
    is_exception_claim = fields.Boolean(
        string="Tramitación por excepción",
        related="repair_id.x_force_warranty_claim",
        readonly=True,
    )

    def _check_can_confirm(self):
        self.ensure_one()
        self.repair_id._check_can_claim_warranty()

    def action_confirm_claim(self):
        self.ensure_one()
        self._check_can_confirm()

        new_repair = self.repair_id._create_warranty_child_repair()
        return {
            "type": "ir.actions.act_window",
            "name": _("RMA de garantía"),
            "res_model": "repair.order",
            "view_mode": "form",
            "res_id": new_repair.id,
        }
