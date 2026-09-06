from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FinishRepair(models.TransientModel):
    _inherit = "wex.finish.repair.glue.choice.wizard"

    wex_requires_glue = fields.Boolean(compute="_compute_billing_options")
    wex_ask_billing = fields.Boolean(compute="_compute_billing_options")
    wex_auto_billing = fields.Boolean(compute="_compute_billing_options")
    wex_billing_choice = fields.Selection([
        ("yes", "Añadir a facturación pendiente"), ("no", "Finalizar sin añadir"),
    ], string="Facturación del cliente portal")

    @api.depends("repair_id")
    def _compute_billing_options(self):
        for wizard in self:
            repair = wizard.repair_id
            offer = bool(repair and repair._should_offer_portal_billing())
            automatic = offer and repair.partner_id.commercial_partner_id.wex_auto_portal_billing
            wizard.wex_requires_glue = bool(repair and repair._requires_glue_choice_on_finish())
            wizard.wex_ask_billing = offer and not automatic
            wizard.wex_auto_billing = automatic

    def _finish_and_set_location(self, location):
        self.ensure_one()
        repair = self.repair_id
        repair._check_portal_billing_access()
        if repair.state != "under_repair":
            raise UserError(_("La reparación ya no está en reparación. Vuelve a abrir su ficha."))
        offer = repair._should_offer_portal_billing()
        automatic = offer and repair.partner_id.commercial_partner_id.wex_auto_portal_billing
        if offer and not automatic and not self.wex_billing_choice:
            raise UserError(_("Indica si quieres añadir el SAT a facturación pendiente."))
        wizard = self.with_context(
            wex_billing_choice_done=True,
            wex_billing_add_on_finish=self.wex_billing_choice == "yes",
        )
        return super(FinishRepair, wizard)._finish_and_set_location(location)

    def action_finish_with_billing(self):
        self.ensure_one()
        if self.repair_id._requires_glue_choice_on_finish():
            raise UserError(_("Selecciona la ubicación final del dispositivo."))
        self.wex_billing_choice = "yes"
        return self._finish_and_set_location(False)

    def action_finish_without_billing(self):
        self.ensure_one()
        if self.repair_id._requires_glue_choice_on_finish():
            raise UserError(_("Selecciona la ubicación final del dispositivo."))
        self.wex_billing_choice = "no"
        return self._finish_and_set_location(False)
