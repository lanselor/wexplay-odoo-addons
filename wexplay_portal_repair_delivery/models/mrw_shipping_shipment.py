# -*- coding: utf-8 -*-

from odoo import models


class MrwShippingShipment(models.Model):
    _inherit = "mrw.shipping.shipment"

    def write(self, vals):
        result = super().write(vals)
        if {"label_attachment_id", "mrw_shipment_number"}.intersection(vals):
            operations = self.env["wex.repair.shipping.operation"].sudo().search(
                [("mrw_shipment_id", "in", self.ids)]
            )
            operations._queue_portal_shipping_notifications_if_ready()
        return result
