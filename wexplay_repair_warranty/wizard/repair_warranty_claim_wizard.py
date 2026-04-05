# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class RepairWarrantyClaimWizard(models.TransientModel):
    _name = "wex.repair.warranty.claim.wizard"
    _description = "Asistente de tramitación de garantía"

    repair_id = fields.Many2one(
        "repair.order",
        string="SAT",
        required=True,
        readonly=True,
    )
    is_out_of_warranty = fields.Boolean(
        string="Fuera de garantía",
        compute="_compute_is_out_of_warranty",
    )
    can_override_expired_warranty = fields.Boolean(
        string="Puede forzar garantía caducada",
        compute="_compute_can_override_expired_warranty",
    )
    override_expired_warranty = fields.Boolean(
        string="Confirmo que desea tramitar igualmente la garantía",
    )

    @api.depends("repair_id", "repair_id.x_is_any_warranty_valid")
    def _compute_is_out_of_warranty(self):
        for wizard in self:
            wizard.is_out_of_warranty = bool(
                wizard.repair_id and not wizard.repair_id.x_is_any_warranty_valid
            )

    @api.depends("repair_id")
    def _compute_can_override_expired_warranty(self):
        for wizard in self:
            wizard.can_override_expired_warranty = bool(
                wizard.repair_id and wizard.repair_id._can_override_expired_warranty()
            )

    def _check_override_permissions(self):
        self.ensure_one()
        if not self.is_out_of_warranty:
            return
        if self.can_override_expired_warranty:
            return
        raise AccessError(
            _("No tiene permisos para forzar la tramitación de una garantía caducada.")
        )

    def _check_can_confirm(self):
        self.ensure_one()
        self.repair_id._check_can_claim_warranty()

        if not self.is_out_of_warranty:
            return

        self._check_override_permissions()
        if self.override_expired_warranty or self.repair_id._is_warranty_claim_forced():
            return

        raise UserError(
            _("Debe confirmar la excepción de garantía caducada para continuar.")
        )

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
