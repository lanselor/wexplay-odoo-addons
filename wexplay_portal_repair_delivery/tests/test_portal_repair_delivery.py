# -*- coding: utf-8 -*-

import base64

from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestPortalRepairDeliveryHTTP(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.company_partner = cls.env["res.partner"].create({"name": "Empresa Envio Portal"})
        cls.contact_partner = cls.env["res.partner"].create(
            {"name": "Contacto Envio Portal", "parent_id": cls.company_partner.id}
        )
        cls.other_partner = cls.env["res.partner"].create({"name": "Otra Empresa Envio"})
        cls.product = cls.env["product.product"].create({"name": "Equipo Envio Portal"})
        cls.portal_password = "portal_delivery_test_123"
        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Portal Delivery User",
                "login": "portal.delivery.wexplay@example.com",
                "email": "portal.delivery.wexplay@example.com",
                "password": cls.portal_password,
                "partner_id": cls.contact_partner.id,
                "groups_id": [(6, 0, [cls.portal_group.id])],
            }
        )
        cls.own_repair = cls._create_repair(cls.company_partner)
        cls.foreign_repair = cls._create_repair(cls.other_partner)
        cls.own_pickup = cls._create_shipping_operation_with_label(
            cls.own_repair,
            "pickup",
        )
        cls.own_delivery = cls._create_shipping_operation_with_label(
            cls.own_repair,
            "delivery",
        )
        cls.foreign_pickup = cls._create_shipping_operation_with_label(
            cls.foreign_repair,
            "pickup",
        )

    @classmethod
    def _create_repair(cls, partner):
        return cls.env["repair.order"].create(
            {
                "partner_id": partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_requires_shipping": True,
            }
        )

    @classmethod
    def _create_shipping_operation_with_label(cls, repair, operation_type):
        picking_type = cls.env["stock.warehouse"].search([], limit=1).out_type_id
        picking = cls.env["stock.picking"].create(
            {
                "partner_id": repair.partner_id.id,
                "picking_type_id": picking_type.id,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": picking_type.default_location_dest_id.id,
                "carrier_tracking_ref": "MRW-PORTAL-TEST",
                "carrier_tracking_url": "https://www.mrw.es/",
            }
        )
        cls.env["ir.attachment"].create(
            {
                "name": "etiqueta-mrw.pdf",
                "type": "binary",
                "datas": base64.b64encode(b"%PDF-1.4 portal label"),
                "mimetype": "application/pdf",
                "res_model": "stock.picking",
                "res_id": picking.id,
            }
        )
        return cls.env["wex.repair.shipping.operation"].create(
            {
                "repair_id": repair.id,
                "operation_type": operation_type,
                "picking_id": picking.id,
            }
        )

    def test_portal_shows_shipping_tab_for_repair_with_logistics(self):
        self.authenticate(self.portal_user.login, self.portal_password)

        response = self.url_open("/my/repairs/%s" % self.own_repair.id)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Envíos", response.text)
        self.assertIn("Recogida del cliente", response.text)
        self.assertIn("Entrega al cliente", response.text)
        self.assertIn("Seguir envío en MRW", response.text)
        self.assertIn("Descargar etiqueta", response.text)

    def test_portal_user_can_download_own_pickup_and_delivery_labels(self):
        self.authenticate(self.portal_user.login, self.portal_password)

        pickup_response = self.url_open(
            "/my/repairs/%s/shipping/%s/label" % (self.own_repair.id, self.own_pickup.id)
        )
        delivery_response = self.url_open(
            "/my/repairs/%s/shipping/%s/label" % (self.own_repair.id, self.own_delivery.id)
        )

        self.assertEqual(pickup_response.status_code, 200)
        self.assertEqual(delivery_response.status_code, 200)
        self.assertEqual(pickup_response.headers["Content-Type"], "application/pdf")
        self.assertEqual(delivery_response.headers["Content-Type"], "application/pdf")

    def test_portal_user_gets_404_for_foreign_shipping_label(self):
        self.authenticate(self.portal_user.login, self.portal_password)

        response = self.url_open(
            "/my/repairs/%s/shipping/%s/label" % (self.foreign_repair.id, self.foreign_pickup.id)
        )

        self.assertEqual(response.status_code, 404)
