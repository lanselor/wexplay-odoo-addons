# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo.tests.common import SavepointCase


class TestPortalRepairSecurity(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.company_partner = cls.env["res.partner"].create({"name": "Empresa Portal"})
        cls.contact_partner = cls.env["res.partner"].create(
            {
                "name": "Contacto Portal",
                "parent_id": cls.company_partner.id,
                "type": "contact",
            }
        )
        cls.other_partner = cls.env["res.partner"].create({"name": "Otra Empresa"})
        cls.product = cls.env["product.product"].create({"name": "Equipo Portal"})
        cls.service_product = cls.env["product.product"].create(
            {
                "name": "Servicio Portal",
                "type": "service",
                "list_price": 42.0,
            }
        )

        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Portal User",
                "login": "portal.user.wexplay@example.com",
                "email": "portal.user.wexplay@example.com",
                "partner_id": cls.contact_partner.id,
                "groups_id": [(6, 0, [cls.portal_group.id])],
            }
        )

        cls.own_repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.company_partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_reported_issue": "No enciende",
            }
        )
        cls.contact_repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.contact_partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_reported_issue": "Pantalla rota",
            }
        )
        cls.foreign_repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.other_partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_reported_issue": "Bateria agotada",
            }
        )
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.company_partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.service_product.id,
                            "name": "Mano de obra portal",
                            "product_uom_qty": 1.0,
                            "product_uom": cls.service_product.uom_id.id,
                            "price_unit": 42.0,
                        },
                    )
                ],
            }
        )
        cls.own_repair.sale_order_id = cls.sale_order

    def test_portal_visible_domain_uses_commercial_partner(self):
        domain = self.env["repair.order"]._get_portal_visible_domain(self.portal_user)
        repairs = self.env["repair.order"].search(domain)

        self.assertIn(self.own_repair, repairs)
        self.assertIn(self.contact_repair, repairs)
        self.assertNotIn(self.foreign_repair, repairs)

    def test_portal_user_only_reads_company_repairs(self):
        portal_repairs = self.env["repair.order"].with_user(self.portal_user).search([])

        self.assertIn(self.own_repair, portal_repairs)
        self.assertIn(self.contact_repair, portal_repairs)
        self.assertNotIn(self.foreign_repair, portal_repairs)

    def test_can_portal_user_access_matches_same_rule(self):
        self.assertTrue(self.own_repair._can_portal_user_access(self.portal_user))
        self.assertTrue(self.contact_repair._can_portal_user_access(self.portal_user))
        self.assertFalse(self.foreign_repair._can_portal_user_access(self.portal_user))

    def test_portal_related_helpers_do_not_bypass_access_with_sudo(self):
        foreign_repair = self.foreign_repair.with_user(self.portal_user)

        with self.assertRaises(AccessError):
            foreign_repair._get_portal_part_line_values()

        with self.assertRaises(AccessError):
            foreign_repair._get_portal_service_line_values()

        with self.assertRaises(AccessError):
            foreign_repair._get_portal_brand_label()

        with self.assertRaises(AccessError):
            foreign_repair._get_portal_image_values()

        with self.assertRaises(AccessError):
            foreign_repair._get_portal_invoice_values()

    def test_portal_user_can_read_prepared_service_lines_from_own_repair(self):
        values = self.own_repair.with_user(self.portal_user)._get_portal_service_line_values()

        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]["name"], self.service_product.display_name)
