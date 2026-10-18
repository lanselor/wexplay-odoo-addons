# -*- coding: utf-8 -*-

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestPortalRepairHTTP(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.company_partner = cls.env["res.partner"].create({"name": "Empresa Portal HTTP"})
        cls.contact_partner = cls.env["res.partner"].create(
            {
                "name": "Contacto Portal HTTP",
                "parent_id": cls.company_partner.id,
                "type": "contact",
            }
        )
        cls.other_partner = cls.env["res.partner"].create({"name": "Otra Empresa HTTP"})
        cls.product = cls.env["product.product"].create({"name": "Equipo Portal HTTP"})
        cls.portal_password = "portal_http_test_123"

        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Portal HTTP User",
                "login": "portal.http.wexplay@example.com",
                "email": "portal.http.wexplay@example.com",
                "password": cls.portal_password,
                "partner_id": cls.contact_partner.id,
                "groups_id": [(6, 0, [cls.portal_group.id])],
            }
        )

        cls.foreign_repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.other_partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_reported_issue": "Foreign repair",
            }
        )
        cls.own_delivered_repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.company_partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "name": "SAT/PORTAL/DELIVERED",
                "state": "delivered" if "delivered" in dict(cls.env["repair.order"]._fields["state"].selection) else "done",
                "x_reported_issue": "Delivered repair",
            }
        )

    def test_portal_user_gets_404_for_foreign_repair_image_route(self):
        self.authenticate(self.portal_user.login, self.portal_password)
        response = self.url_open(
            "/my/repairs/%s/images/999999?variant=thumb" % self.foreign_repair.id
        )
        self.assertEqual(response.status_code, 404)

    def test_portal_repairs_page_keeps_filters_visible_when_active_is_empty(self):
        self.authenticate(self.portal_user.login, self.portal_password)

        response = self.url_open("/my/repairs")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Finalizados", response.text)
        self.assertIn("Todos", response.text)
        self.assertIn("/my/repairs?filterby=done", response.text)

    def test_portal_done_filter_lists_delivered_repairs(self):
        self.authenticate(self.portal_user.login, self.portal_password)

        response = self.url_open("/my/repairs?filterby=done")

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.own_delivered_repair.name, response.text)

    def test_portal_inspection_card_is_inside_ficha_and_escaped(self):
        from lxml import html
        self.own_delivered_repair.write({
            "x_device_type": "mobile", "x_device_description": "Recorded <script>unsafe()</script> & text",
            "x_device_inspection_marks": {"device_type": "mobile", "front": [[[0.1, 0.2]]], "back": []},
            "x_internal_notes": "PRIVATE PORTAL INSPECTION NOTE",
        })
        self.authenticate(self.portal_user.login, self.portal_password)
        response = self.url_open("/my/repairs/%s" % self.own_delivered_repair.id)
        self.assertEqual(response.status_code, 200)
        tree = html.fromstring(response.content)
        section = tree.xpath("//div[@id='tab-ficha']//section[contains(@class,'wex_portal_inspection')]")
        self.assertEqual(len(section), 1)
        self.assertIn(self.own_delivered_repair.x_device_description, section[0].text_content())
        self.assertFalse(section[0].xpath(".//script"))
        self.assertEqual(len(section[0].xpath(".//details//img")), 2)
        self.assertFalse(section[0].xpath(".//details[@open]"))
        self.assertFalse(tree.xpath("//div[@id='tab-reparacion']//section[contains(@class,'wex_portal_inspection')]"))
        self.assertNotIn("PRIVATE PORTAL INSPECTION NOTE", response.text)

    def test_foreign_repair_inspection_is_not_accessible_by_url(self):
        self.foreign_repair.write({"x_device_type": "mobile", "x_device_description": "FOREIGN INSPECTION SECRET"})
        self.authenticate(self.portal_user.login, self.portal_password)
        response = self.url_open("/my/repairs/%s" % self.foreign_repair.id)
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("FOREIGN INSPECTION SECRET", response.text)

    def test_anonymous_user_cannot_read_inspection(self):
        self.own_delivered_repair.write({"x_device_type": "mobile", "x_device_description": "AUTHENTICATED INSPECTION ONLY"})
        response = self.url_open("/my/repairs/%s" % self.own_delivered_repair.id)
        self.assertNotIn("AUTHENTICATED INSPECTION ONLY", response.text)
        self.assertIn("/web/login", response.url)
