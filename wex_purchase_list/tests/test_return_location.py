from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestReturnLocation(TransactionCase):
    def test_company_location_is_created_and_preserved(self):
        company = self.env["res.company"].create({"name": "Return location test"})
        location = company.wex_return_location_id
        self.assertEqual(location.company_id, company)
        self.assertEqual(location.usage, "internal")
        company._ensure_wex_return_location()
        self.assertEqual(company.wex_return_location_id, location)

    def test_location_cannot_be_warehouse_stock(self):
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        self.assertTrue(warehouse)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env.company.wex_return_location_id = warehouse.lot_stock_id

    def test_custom_selection_survives_initialization(self):
        company = self.env["res.company"].create({"name": "Custom return location test"})
        custom = self.env["stock.location"].create({
            "name": "Custom returns", "usage": "internal", "company_id": company.id,
            "location_id": self.env.ref("stock.stock_location_locations").id,
        })
        company.wex_return_location_id = custom
        company._ensure_wex_return_location()
        self.assertEqual(company.wex_return_location_id, custom)

    def test_foreign_company_location_is_rejected(self):
        other = self.env["res.company"].create({"name": "Foreign return location test"})
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env.company.wex_return_location_id = other.wex_return_location_id

    def test_stock_descendant_is_rejected(self):
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        child = self.env["stock.location"].create({
            "name": "Inside stock", "location_id": warehouse.lot_stock_id.id,
            "usage": "internal", "company_id": self.env.company.id,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env.company.wex_return_location_id = child

    def test_supplier_and_inactive_locations_are_rejected(self):
        for vals in ({"usage": "supplier"}, {"usage": "internal", "active": False}):
            location = self.env["stock.location"].create({
                "name": "Invalid return location", "company_id": self.env.company.id, **vals,
            })
            with self.assertRaises(ValidationError), self.cr.savepoint():
                self.env.company.wex_return_location_id = location

    def test_default_location_is_outside_normal_stock_availability(self):
        warehouse = self.env["stock.warehouse"].search([("company_id", "=", self.env.company.id)], limit=1)
        self.env.company._ensure_wex_return_location()
        product = self.env["product.product"].create({
            "name": "Return location isolation test", "type": "consu", "is_storable": True,
        })
        quant_model = self.env["stock.quant"]
        location = self.env.company.wex_return_location_id
        quant_model._update_available_quantity(product, location, 5)
        self.assertEqual(quant_model._get_available_quantity(product, warehouse.lot_stock_id), 0)
        self.assertEqual(quant_model._get_available_quantity(product, location), 5)

    def test_repair_supply_location_is_rejected(self):
        source = self.env["stock.location"].create({
            "name": "SAT supply test", "usage": "internal", "company_id": self.env.company.id,
            "location_id": self.env.ref("stock.stock_location_locations").id,
        })
        self.env["stock.picking.type"].create({
            "name": "SAT supply test", "code": "repair_operation", "sequence_code": "RETTEST",
            "company_id": self.env.company.id, "default_location_src_id": source.id,
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env.company.wex_return_location_id = source

    def test_settings_are_present_and_menu_targets_purchase(self):
        from lxml import etree

        view = self.env["res.config.settings"].get_view(view_type="form")
        form = etree.fromstring(view["arch"])
        self.assertTrue(form.xpath("//app[@name='purchase']//field[@name='wex_return_location_id']"))
        action = self.env.ref("wex_purchase_list.menu_wex_purchase_return_settings").action
        self.assertEqual(action.res_model, "res.config.settings")
        self.assertIn("purchase", action.context)
