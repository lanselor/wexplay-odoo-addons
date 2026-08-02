from odoo.tests.common import TransactionCase


class TestSaleOrderReservationPolicy(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "Customer"})
        cls.vendor = cls.env["res.partner"].create({
            "name": "Vendor",
            "supplier_rank": 1,
        })
        cls.product = cls.env["product.product"].create({"name": "Purchase List Product"})

    def _create_sale_purchase_line(self, *, customer_notified=False):
        order = self.env["sale.order"].create({"partner_id": self.customer.id})
        sale_line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.product.id,
            "product_uom_qty": 1,
        })
        purchase_line = self.env["wex_purchase_list.line"].create({
            "product_id": self.product.id,
            "quantity": 1,
            "vendor_id": self.vendor.id,
            "customer_id": self.customer.id,
            "sale_line_id": sale_line.id,
            "is_reservation": True,
            "customer_notified": customer_notified,
            "state": "to_purchase",
        })
        return order, purchase_line

    def test_reservation_policy_syncs_active_purchase_lines(self):
        order, purchase_line = self._create_sale_purchase_line()

        order.wex_purchase_list_is_reservation = False

        self.assertFalse(purchase_line.is_reservation)

    def test_reservation_policy_keeps_notified_history(self):
        order, purchase_line = self._create_sale_purchase_line(customer_notified=True)

        order.wex_purchase_list_is_reservation = False

        self.assertTrue(purchase_line.is_reservation)
