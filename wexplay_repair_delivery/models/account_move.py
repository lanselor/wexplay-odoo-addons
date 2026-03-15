# -*- coding: utf-8 -*-
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def wex_get_sat_repairs(self):
        self.ensure_one()

        _logger.warning(
            "WEX DELIVERY DEBUG | wex_get_sat_repairs | invoice id=%s name=%s payment_state=%s",
            self.id, self.name, self.payment_state
        )

        if hasattr(self, "_get_sat_repairs"):
            repairs = self._get_sat_repairs()
            _logger.warning(
                "WEX DELIVERY DEBUG | _get_sat_repairs() returned ids=%s names=%s",
                repairs.ids,
                repairs.mapped("name"),
            )
            return repairs

        sale_orders = self.invoice_line_ids.sale_line_ids.order_id.filtered(lambda so: so)

        _logger.warning(
            "WEX DELIVERY DEBUG | fallback sale_orders ids=%s names=%s",
            sale_orders.ids,
            sale_orders.mapped("name"),
        )

        if not sale_orders:
            _logger.warning("WEX DELIVERY DEBUG | no sale orders linked to invoice")
            return self.env["repair.order"]

        repairs = self.env["repair.order"].search([
            ("sale_order_id", "in", sale_orders.ids),
        ], order="id desc")

        _logger.warning(
            "WEX DELIVERY DEBUG | fallback repairs ids=%s names=%s",
            repairs.ids,
            repairs.mapped("name"),
        )

        return repairs