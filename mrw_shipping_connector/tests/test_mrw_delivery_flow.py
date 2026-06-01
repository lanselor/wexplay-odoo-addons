from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestMRWDeliveryFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_es = cls.env.ref("base.es")
        cls.country_fr = cls.env.ref("base.fr")
        cls.national_service = cls.env["mrw.shipping.service"].create(
            {
                "name": "Test Bag 19",
                "code": "T0230",
                "service_type": "national",
            }
        )
        cls.international_service = cls.env["mrw.shipping.service"].create(
            {
                "name": "Test Internacional",
                "code": "TINT",
                "service_type": "international",
            }
        )
        cls.config = cls.env["mrw.shipping.config"].create(
            {
                "name": "Test MRW",
                "company_id": cls.env.company.id,
                "environment": "test",
                "agency_code": "01400",
                "subscriber_code": "003429",
                "username": "01400PSWEXP",
                "password": "secret",
                "default_national_service_id": cls.national_service.id,
                "default_international_service_id": cls.international_service.id,
            }
        )
        cls.delivery_product = cls.env["product.product"].create(
            {
                "name": "MRW Test Delivery Product",
                "type": "service",
                "list_price": 0.0,
            }
        )
        cls.carrier = cls.env["delivery.carrier"].create(
            {
                "name": "MRW Test Carrier",
                "delivery_type": "mrw",
                "product_id": cls.delivery_product.id,
                "mrw_config_id": cls.config.id,
                "mrw_service_id": cls.national_service.id,
            }
        )
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.stock_location = cls.env.ref("stock.stock_location_stock")
        cls.outgoing_type = cls.env.ref("stock.picking_type_out")
        cls.internal_type = cls.env.ref("stock.picking_type_internal")

    def _partner(self, country):
        return self.env["res.partner"].create(
            {
                "name": "Alex Prueba",
                "phone": "+34 650 27 94 87",
                "street": "Agra de Bragua 51 Bajo",
                "zip": "15010",
                "city": "A Coruna",
                "country_id": country.id,
            }
        )

    def _picking(self, picking_type, destination, partner):
        return self.env["stock.picking"].create(
            {
                "partner_id": partner.id,
                "picking_type_id": picking_type.id,
                "location_id": self.stock_location.id,
                "location_dest_id": destination.id,
                "carrier_id": self.carrier.id,
            }
        )

    def test_mrw_rejects_internal_transfer_before_api_call(self):
        picking = self._picking(
            self.internal_type,
            self.stock_location,
            self._partner(self.country_es),
        )

        with self.assertRaisesRegex(UserError, "outgoing delivery orders"):
            self.carrier._mrw_check_picking_can_be_sent(picking)

    def test_mrw_rejects_international_when_config_switch_is_disabled(self):
        self.carrier.mrw_service_id = self.international_service
        picking = self._picking(
            self.outgoing_type,
            self.customer_location,
            self._partner(self.country_fr),
        )

        with self.assertRaisesRegex(UserError, "international shipments are not enabled"):
            self.carrier._mrw_check_picking_can_be_sent(picking)

    def test_mrw_tracking_link_uses_public_history_url(self):
        picking = self._picking(
            self.outgoing_type,
            self.customer_location,
            self._partner(self.country_es),
        )
        picking.carrier_tracking_ref = "01400F001137"

        link = self.carrier.mrw_get_tracking_link(picking)

        self.assertEqual(
            link,
            "http://www.mrw.es/seguimiento_envios/MRW_historico_nacional.asp?enviament=01400F001137",
        )

    def test_existing_tracking_is_recovered_without_creating_new_remote_attempt(self):
        picking = self._picking(
            self.outgoing_type,
            self.customer_location,
            self._partner(self.country_es),
        )
        picking.carrier_tracking_ref = "01400F280052"

        shipment = self.carrier._mrw_get_or_create_shipment_from_picking(picking)

        self.assertTrue(shipment)
        self.assertEqual(shipment.state, "sent")
        self.assertEqual(shipment.mrw_shipment_number, "01400F280052")
        self.assertEqual(picking.mrw_shipment_id, shipment)
        self.assertEqual(picking.carrier_tracking_ref, "01400F280052")

    def test_production_calls_are_blocked_without_explicit_enablement(self):
        shipment = self.env["mrw.shipping.shipment"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.config.id,
                "service_id": self.national_service.id,
                "shipment_type": "national",
                "partner_id": self._partner(self.country_es).id,
                "recipient_name": "Alex Prueba",
                "recipient_phone": "650279487",
                "street": "Agra de Bragua 51 Bajo",
                "zip": "15010",
                "city": "A Coruna",
                "country_id": self.country_es.id,
                "reference": "TEST-PROD",
            }
        )
        self.env["mrw.shipping.package"].create(
            {
                "shipment_id": shipment.id,
                "sequence": 1,
                "weight": 1,
                "height": 1,
                "width": 1,
                "length": 1,
            }
        )
        shipment.action_prepare()
        self.config.environment = "production"

        with self.assertRaisesRegex(UserError, "producción"):
            shipment._check_can_send_to_mrw()

    def test_customer_pickup_can_create_incoming_picking(self):
        partner = self._partner(self.country_es)
        product = self.env["product.product"].create(
            {
                "name": "Tablet RMA",
                "type": "consu",
                "is_storable": True,
            }
        )
        shipment = self.env["mrw.shipping.shipment"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.config.id,
                "service_id": self.national_service.id,
                "shipment_type": "national",
                "movement_type": "pickup",
                "partner_id": partner.id,
                "recipient_name": partner.name,
                "recipient_phone": partner.phone,
                "street": partner.street,
                "zip": partner.zip,
                "city": partner.city,
                "country_id": self.country_es.id,
                "reference": "RMA-001",
                "stock_product_id": product.id,
                "stock_product_uom_qty": 1.0,
            }
        )

        shipment.action_create_incoming_picking()

        self.assertTrue(shipment.picking_id)
        self.assertEqual(shipment.picking_id.picking_type_code, "incoming")
        self.assertEqual(shipment.picking_id.partner_id, partner)
        self.assertEqual(shipment.picking_id.location_id, partner.property_stock_customer)
        self.assertEqual(shipment.picking_id.mrw_shipment_id, shipment)
        self.assertEqual(
            shipment.picking_id.move_ids_without_package.product_id,
            product,
        )

    def test_manual_shipment_defaults_reference_to_sequence_name(self):
        shipment = self.env["mrw.shipping.shipment"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.config.id,
                "service_id": self.national_service.id,
                "shipment_type": "national",
                "partner_id": self._partner(self.country_es).id,
                "recipient_name": "Alex Prueba",
                "recipient_phone": "650279487",
                "street": "Agra de Bragua 51 Bajo",
                "zip": "15010",
                "city": "A Coruna",
                "country_id": self.country_es.id,
            }
        )

        self.assertTrue(shipment.name)
        self.assertEqual(shipment.reference, shipment.name)

    def test_manual_shipment_default_get_includes_one_package(self):
        defaults = self.env["mrw.shipping.shipment"].default_get(["package_ids"])

        self.assertTrue(defaults["package_ids"])
        command = defaults["package_ids"][0]
        self.assertEqual(command[0], 0)
        self.assertEqual(command[2]["sequence"], 1)
        self.assertEqual(command[2]["weight"], 1.0)
