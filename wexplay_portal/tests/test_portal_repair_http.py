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

    def test_portal_user_gets_404_for_foreign_repair_image_route(self):
        self.authenticate(self.portal_user.login, self.portal_password)
        response = self.url_open(
            "/my/repairs/%s/images/999999?variant=thumb" % self.foreign_repair.id
        )
        self.assertEqual(response.status_code, 404)
