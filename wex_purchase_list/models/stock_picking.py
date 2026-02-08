from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()

        # post-validación: si es recepción ligada a compra
        for picking in self:
            purchase = picking.purchase_id
            if not purchase:
                continue

            # buscar líneas wex por purchase_order_line_id
            wex_lines = self.env["wex_purchase_list.line"].search([
                ("purchase_order_id", "=", purchase.id),
                ("purchase_order_line_id", "!=", False),
                ("state", "=", "ordered"),
            ])

            if not wex_lines:
                continue

            # map pol -> received?
            received_pol_ids = set()
            for pol in purchase.order_line:
                # recibido completo
                if pol.qty_received >= pol.product_qty:
                    received_pol_ids.add(pol.id)

            to_receive = wex_lines.filtered(lambda l: l.purchase_order_line_id.id in received_pol_ids)
            if to_receive:
                to_receive.write({"state": "received"})

        return res
