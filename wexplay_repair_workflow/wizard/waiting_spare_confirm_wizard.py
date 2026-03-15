# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import UserError


class WexWaitingSpareConfirmWizard(models.TransientModel):
    _name = "wex.waiting.spare.confirm.wizard"
    _description = "Confirmar paso a pendiente de repuesto"

    repair_id = fields.Many2one(
        "repair.order",
        string="Reparación",
        required=True,
        readonly=True,
    )

    def action_confirm_waiting_spare(self):
        self.ensure_one()
        repair = self.repair_id
        if not repair:
            raise UserError(_("No se ha encontrado la reparación."))
        return repair.with_context(skip_waiting_spare_confirm=True).action_set_waiting_spare()