from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestPurchaseReturnFoundation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "Return test vendor", "supplier_rank": 1})
        cls.product = cls.env["product.product"].create({
            "name": "Return test part", "type": "consu", "is_storable": True,
        })
        cls.order = cls.env["purchase.order"].create({
            "partner_id": cls.vendor.id,
            "order_line": [Command.create({
                "product_id": cls.product.id, "name": cls.product.name,
                "product_qty": 2, "product_uom": cls.product.uom_po_id.id,
                "price_unit": 10,
            })],
        })
        cls.order.button_confirm()
        cls.receipt = cls.order.picking_ids
        cls.move = cls.receipt.move_ids
        cls.move.quantity = 2
        cls.move.picked = True
        cls.receipt.button_validate()
        cls.line = cls.env["wex_purchase_list.line"].create({
            "product_id": cls.product.id, "vendor_id": cls.vendor.id,
            "quantity": 2, "state": "received",
            "purchase_order_id": cls.order.id,
            "purchase_order_line_id": cls.order.order_line.id,
        })

    def _create_tracking(self, **values):
        return self.env["wex.purchase.return"].create({
            "purchase_list_line_id": self.line.id, "receipt_move_id": self.move.id,
            "quantity": 1, **values,
        })

    def test_links_are_available_without_stock_operations(self):
        before = self.env["stock.picking"].search_count([])
        record = self._create_tracking(rma_reference="RMA-123")
        self.assertEqual(record.purchase_order_id, self.order)
        self.assertEqual(record.receipt_picking_id, self.receipt)
        self.assertEqual(record.vendor_id, self.vendor)
        self.assertEqual(record.product_id, self.product)
        self.assertEqual(record.rma_reference, "RMA-123")
        self.assertEqual(self.env["stock.picking"].search_count([]), before)
        self.assertEqual(self.move.quantity, 2)

    def test_invalid_quantities(self):
        for quantity in (0, -1, 3):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self._create_tracking(quantity=quantity)

    def test_unreceived_move_is_rejected(self):
        draft = self.move.copy({"picking_id": False, "state": "draft"})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._create_tracking(receipt_move_id=draft.id)

    def test_other_purchase_line_is_rejected(self):
        other = self.order.order_line.copy({"order_id": self.order.id})
        self.line.purchase_order_line_id = other
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._create_tracking()

    def test_source_edit_cannot_break_existing_traceability(self):
        self._create_tracking()
        other = self.order.order_line.copy({"order_id": self.order.id})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.line.purchase_order_line_id = other

    def test_foreign_company_is_rejected(self):
        other = self.env["res.company"].create({"name": "Foreign return company"})
        with self.assertRaises(UserError), self.cr.savepoint():
            self._create_tracking(company_id=other.id)

    def test_tracking_cannot_be_copied(self):
        record = self._create_tracking()
        with self.assertRaises(UserError):
            record.copy()

    def test_picking_links_are_checked(self):
        for field in ("internal_picking_id", "return_picking_id"):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self._create_tracking(**{field: self.receipt.id})

    def test_company_rule_applies_to_managers_and_users(self):
        record = self._create_tracking()
        other = self.env["res.company"].create({"name": "Return security company"})
        for group in ("group_wex_purchase_list_user", "group_wex_purchase_list_manager"):
            user = new_test_user(
                self.env, login=group, groups="base.group_user,wex_purchase_list." + group,
                company_id=self.env.company.id,
                company_ids=[Command.set([self.env.company.id, other.id])],
            )
            allowed = record.with_user(user).with_context(allowed_company_ids=[self.env.company.id])
            self.assertEqual(allowed.read(["quantity"])[0]["quantity"], 1)
            foreign = record.with_user(user).with_context(allowed_company_ids=[other.id])
            with self.assertRaises(AccessError):
                foreign.read(["quantity"])
            if group == "group_wex_purchase_list_user":
                with self.assertRaises(AccessError), self.cr.savepoint():
                    self.env["wex.purchase.return"].with_user(user).create({
                        "purchase_list_line_id": self.line.id,
                        "receipt_move_id": self.move.id, "quantity": 1,
                    })
