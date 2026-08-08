# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError


class MrwShippingShipment(models.Model):
    _inherit = "mrw.shipping.shipment"

    def action_open_mrw_whatsapp(self):
        self.ensure_one()
        if not self.mrw_shipment_number:
            raise UserError(_("El envío debe estar confirmado por MRW antes de abrir WhatsApp."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Redactar WhatsApp MRW"),
            "res_model": "whatsapp.compose.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
            },
        }
