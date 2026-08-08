# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError


class WexRepairShippingOperation(models.Model):
    _inherit = "wex.repair.shipping.operation"

    def action_open_mrw_whatsapp(self):
        self.ensure_one()
        if not self.mrw_shipment_id:
            raise UserError(_("La operación todavía no tiene un envío MRW confirmado."))
        return self.mrw_shipment_id.action_open_mrw_whatsapp()
