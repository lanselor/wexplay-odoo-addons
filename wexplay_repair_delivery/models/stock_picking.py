# -*- coding: utf-8 -*-

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    x_repair_shipping_operation_id = fields.Many2one(
        comodel_name="wex.repair.shipping.operation",
        string="Operación logística SAT",
        copy=False,
        index=True,
        ondelete="set null",
        help="Operación logística SAT que originó este albarán.",
    )
    x_repair_delivery_order_id = fields.Many2one(
        related="x_repair_shipping_operation_id.repair_id",
        string="Reparación SAT",
        store=True,
        readonly=True,
    )

    def button_validate(self):
        result = super().button_validate()
        for picking in self.filtered(
            lambda picking: picking.state == "done"
            and picking.x_repair_shipping_operation_id
        ):
            operation = picking.x_repair_shipping_operation_id
            if operation.operation_type == "pickup" and not operation.mrw_shipment_id:
                continue
            operation.state = "done"
        return result
