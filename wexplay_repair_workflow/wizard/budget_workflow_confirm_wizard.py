# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import UserError


class WexBudgetWorkflowConfirmWizard(models.TransientModel):
    _name = "wex.budget.workflow.confirm.wizard"
    _description = "Confirmaciones del workflow de presupuesto SAT"

    repair_id = fields.Many2one(
        "repair.order",
        string="Reparacion",
        required=True,
        readonly=True,
    )
    action_key = fields.Selection(
        [
            ("wait_customer_without_quote", "Espera cliente sin cotizacion"),
            ("reject_budget", "Rechazar presupuesto"),
            ("reestimate_budget_reset_quote", "Volver a presupuestar con cotizacion a borrador"),
        ],
        string="Accion",
        required=True,
        readonly=True,
    )
    message = fields.Text(
        string="Mensaje",
        readonly=True,
    )

    def _get_confirm_action(self):
        self.ensure_one()
        action_map = {
            "wait_customer_without_quote": (
                self.repair_id.with_context(skip_budget_wait_customer_quote_confirm=True)
                .action_budget_wait_customer
            ),
            "reject_budget": (
                self.repair_id.with_context(skip_budget_reject_confirm=True)
                .action_budget_reject
            ),
            "reestimate_budget_reset_quote": (
                self.repair_id.with_context(
                    skip_budget_reestimate_quote_reset_confirm=True
                ).action_budget_reestimate
            ),
        }
        return action_map.get(self.action_key)

    def action_confirm(self):
        self.ensure_one()
        if not self.repair_id:
            raise UserError(_("No se ha encontrado la reparacion."))

        action = self._get_confirm_action()
        if not action:
            raise UserError(_("La accion a confirmar no es valida."))

        return action()
