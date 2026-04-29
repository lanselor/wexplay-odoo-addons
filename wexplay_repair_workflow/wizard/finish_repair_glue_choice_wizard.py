# -*- coding: utf-8 -*-

from odoo import _, models, fields
from odoo.exceptions import UserError


class WexFinishRepairGlueChoiceWizard(models.TransientModel):
    _name = "wex.finish.repair.glue.choice.wizard"
    _description = "Elegir ubicación final al finalizar reparación"

    repair_id = fields.Many2one(
        "repair.order",
        string="Reparación",
        required=True,
        readonly=True,
    )

    def _finish_and_set_location(self, location):
        self.ensure_one()
        repair = self.repair_id

        if not repair:
            raise UserError(_("No se ha encontrado la reparación."))

        repair.with_context(
            skip_glue_finish_wizard=True,
            skip_repair_state_location_sync=True,
        ).action_repair_end()

        if location:
            repair.write({"product_location_src_id": location.id})

        return {"type": "ir.actions.act_window_close"}

    def action_finish_to_glue_desk(self):
        self.ensure_one()
        repair = self.repair_id
        location = repair.company_id.x_repair_state_location_glue_desk_id
        if not location:
            raise UserError(_("Configura primero la ubicación 'Mesa Pegado' en Ajustes > Wexplay SAT."))
        return self._finish_and_set_location(location)

    def action_finish_to_pickup(self):
        self.ensure_one()
        repair = self.repair_id
        location = repair.company_id.x_repair_state_location_done_id
        if not location:
            raise UserError(_("Configura primero la ubicación 'Finalizada' en Ajustes > Wexplay SAT."))
        return self._finish_and_set_location(location)
