# -*- coding: utf-8 -*-
from odoo import fields, models, _


class RepairDeliveryWizard(models.TransientModel):
    _name = "wex.repair.delivery.wizard"
    _description = "Confirmar entrega de reparación SAT"

    repair_id = fields.Many2one(
        "repair.order",
        string="Orden de reparación",
        required=True,
        readonly=True,
    )

    invoice_id = fields.Many2one(
        "account.move",
        string="Factura",
        required=True,
        readonly=True,
    )

    message_html = fields.Html(
        string="Mensaje",
        compute="_compute_message_html",
        sanitize=False,
    )

    def _compute_message_html(self):
        for wizard in self:
            repair_name = wizard.repair_id.name or "-"
            invoice_name = wizard.invoice_id.name or wizard.invoice_id.ref or "-"
            wizard.message_html = _(
                "<p>Acabas de registrar el pago de la factura <strong>%s</strong> "
                "relacionada con la orden de reparación <strong>%s</strong>.</p>"
                "<p>¿Deseas marcar la reparación como entregada al cliente?</p>"
            ) % (invoice_name, repair_name)

    def action_mark_delivered(self):
        self.ensure_one()
        self.repair_id.action_mark_delivered()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Reparación entregada"),
                "message": _(
                    "La orden de trabajo %s se ha marcado como entregada."
                ) % (self.repair_id.name or ""),
                "type": "success",
                "sticky": False,
            },
        }

    def action_do_nothing(self):
        return {"type": "ir.actions.act_window_close"}