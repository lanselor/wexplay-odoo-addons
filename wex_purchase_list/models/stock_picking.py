from odoo import _, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        reservation_lines_to_notify = self.env["wex_purchase_list.line"]

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
                to_receive.action_mark_as_received()
                reservation_lines_to_notify |= to_receive.filtered(
                    lambda line: line.is_reservation and not line.customer_notified
                )

        if reservation_lines_to_notify and res is True:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Reservas listas para avisar"),
                    "message": _(
                        "%s reserva(s) han llegado y quedan pendientes de avisar al cliente."
                    ) % len(reservation_lines_to_notify),
                    "type": "warning",
                    "sticky": True,
                },
            }

        return res
