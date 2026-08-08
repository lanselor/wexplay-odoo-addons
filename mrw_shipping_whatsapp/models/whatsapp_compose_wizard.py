# -*- coding: utf-8 -*-

from odoo import api, fields, models


MRW_WHATSAPP_MODEL = "mrw.shipping.shipment"


class WhatsappComposeWizard(models.TransientModel):
    _inherit = "whatsapp.compose.wizard"

    res_model = fields.Selection(
        selection_add=[(MRW_WHATSAPP_MODEL, "MRW: Envío")],
        ondelete={MRW_WHATSAPP_MODEL: "set default"},
    )

    @api.model
    def _get_supported_res_models(self):
        return super()._get_supported_res_models() | {MRW_WHATSAPP_MODEL}

    def _render_placeholder(self, expr, render_context):
        shipment = render_context["object"]
        if shipment and shipment._name == MRW_WHATSAPP_MODEL:
            values = {
                "mrw_reference": shipment.reference or shipment.name,
                "mrw_tracking_number": shipment.mrw_shipment_number or "",
                "mrw_tracking_url": shipment._get_tracking_url() or "",
            }
            key = (expr or "").strip()
            if key in values:
                return values[key] or self._format_unresolved_placeholder(key)
        return super()._render_placeholder(expr, render_context)
