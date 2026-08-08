# -*- coding: utf-8 -*-

from odoo import api, fields, models


class WhatsappTemplate(models.Model):
    _inherit = "whatsapp.template"

    res_model = fields.Selection(
        selection_add=[("mrw.shipping.shipment", "MRW: Envío")],
        ondelete={"mrw.shipping.shipment": "cascade"},
    )
    context_group = fields.Selection(
        selection_add=[("mrw_shipping", "MRW: Envío / Recogida")],
        ondelete={"mrw_shipping": "set default"},
    )

    @api.model
    def _get_default_context_group(self, res_model):
        if res_model == "mrw.shipping.shipment":
            return "mrw_shipping"
        return super()._get_default_context_group(res_model)

    @api.model
    def _get_allowed_context_groups_by_model(self):
        allowed = super()._get_allowed_context_groups_by_model()
        allowed["mrw.shipping.shipment"] = {"general", "mrw_shipping"}
        return allowed
