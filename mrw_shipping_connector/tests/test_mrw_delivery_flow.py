from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

from odoo.addons.mrw_shipping_connector.services.mrw_client import MRWClient


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

    def test_manual_tracking_query_stores_mrw_status_without_changing_shipment_state(self):
        partner = self._partner(self.country_es)
        shipment = self.env["mrw.shipping.shipment"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.config.id,
                "service_id": self.national_service.id,
                "shipment_type": "national",
                "partner_id": partner.id,
                "recipient_name": partner.name,
                "recipient_phone": partner.phone,
                "street": partner.street,
                "zip": partner.zip,
                "city": partner.city,
                "country_id": self.country_es.id,
                "reference": "TRACKING-001",
            }
        )
        shipment.write({"mrw_shipment_number": "01400F001137", "state": "sent"})
        self.config.enable_tracking_queries = True
        soap_response = """<?xml version=\"1.0\"?>
            <soap:Envelope xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\">
              <soap:Body>
                <SeguimientoNumeroEnvioMRWNacionalResponse xmlns=\"http://www.mrw.es/webservices/seguimiento\">
                  <SeguimientoNumeroEnvioMRWNacionalResult>
                    <Estado>true</Estado><Mensaje>Consulta correcta</Mensaje>
                    <Envio><Numero>01400F001137</Numero><Estado>01</Estado><EstadoDescripcion>En tránsito</EstadoDescripcion></Envio>
                  </SeguimientoNumeroEnvioMRWNacionalResult>
                </SeguimientoNumeroEnvioMRWNacionalResponse>
              </soap:Body>
            </soap:Envelope>"""

        with patch.object(MRWClient, "_call_tracking", return_value=soap_response):
            shipment.action_get_mrw_tracking()

        self.assertEqual(shipment.state, "sent")
        self.assertEqual(shipment.mrw_tracking_status_code, "01")
        self.assertEqual(shipment.mrw_tracking_status_description, "En tránsito")
        log = self.env["mrw.shipping.log"].search(
            [("shipment_id", "=", shipment.id), ("operation", "=", "get_tracking")],
            limit=1,
        )
        self.assertEqual(log.status, "success")
        self.assertNotIn(self.config.password, log.request_raw)

    def test_manual_tracking_query_keeps_malformed_mrw_response_in_log(self):
        partner = self._partner(self.country_es)
        shipment = self.env["mrw.shipping.shipment"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.config.id,
                "service_id": self.national_service.id,
                "shipment_type": "national",
                "partner_id": partner.id,
                "recipient_name": partner.name,
                "recipient_phone": partner.phone,
                "street": partner.street,
                "zip": partner.zip,
                "city": partner.city,
                "country_id": self.country_es.id,
                "reference": "TRACKING-MALFORMED-001",
            }
        )
        shipment.write({"mrw_shipment_number": "01400F001138", "state": "sent"})
        self.config.enable_tracking_queries = True
        malformed_response = "<Envelope><Body><Envio></Body></Envelope>"

        with patch.object(
            MRWClient, "_call_tracking", return_value=malformed_response
        ):
            shipment.action_get_mrw_tracking()

        log = self.env["mrw.shipping.log"].search(
            [("shipment_id", "=", shipment.id), ("operation", "=", "get_tracking")],
            limit=1,
        )
        self.assertEqual(log.status, "error")
        self.assertEqual(log.response_raw, malformed_response)
        self.assertIn("<Password>***</Password>", log.request_raw)

    def test_tracking_endpoint_forces_https_for_legacy_http_configuration(self):
        self.config.tracking_wsdl_url = (
            "http://seguimiento.mrw.es/swc/wssgmntnvs.asmx?WSDL"
        )

        endpoint = MRWClient(self.config)._get_tracking_endpoint()

        self.assertEqual(endpoint, "https://seguimiento.mrw.es/swc/wssgmntnvs.asmx")

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
        self.assertTrue(shipment.package_ids)
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

    def test_notification_sends_tracking_email_and_keeps_history(self):
        partner = self._partner(self.country_es)
        partner.email = "customer@example.com"
        shipment = self.env["mrw.shipping.shipment"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.config.id,
                "service_id": self.national_service.id,
                "shipment_type": "national",
                "partner_id": partner.id,
                "recipient_name": partner.name,
                "recipient_phone": partner.phone,
                "street": partner.street,
                "zip": partner.zip,
                "city": partner.city,
                "country_id": self.country_es.id,
                "reference": "NOTIFY-001",
            }
        )
        self.assertTrue(shipment.package_ids)
        shipment.write(
            {
                "mrw_shipment_number": "NOTIFY-%s" % shipment.id,
                "state": "sent",
            }
        )
        template = self.env.ref(
            "mrw_shipping_connector.mail_template_mrw_shipment_created"
        )

        with patch.object(type(template), "send_mail", return_value=False) as send_mail:
            notification = self.env["mrw.shipping.notification"].send_customer_notification(
                shipment,
                "shipment_created",
                partner.email,
            )

        self.assertEqual(notification.state, "sent")
        self.assertEqual(notification.recipient_email, partner.email)
        self.assertFalse(notification.attachment_id)
        send_mail.assert_called_once()
        self.assertEqual(shipment.notification_count, 1)

    def test_pickup_label_notification_requires_and_attaches_label(self):
        partner = self._partner(self.country_es)
        partner.email = "pickup@example.com"
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
                "reference": "PICKUP-NOTIFY-001",
            }
        )
        self.assertTrue(shipment.package_ids)
        shipment.write(
            {
                "mrw_shipment_number": "PICKUP-NOTIFY-%s" % shipment.id,
                "state": "sent",
            }
        )
        notification_model = self.env["mrw.shipping.notification"]

        with self.assertRaisesRegex(UserError, "obtener la etiqueta"):
            notification_model.send_customer_notification(
                shipment, "pickup_label_ready", partner.email
            )

        attachment = self.env["ir.attachment"].create(
            {
                "name": "pickup-label.pdf",
                "type": "binary",
                "datas": "JVBERi0xLjQ=",
                "res_model": "mrw.shipping.shipment",
                "res_id": shipment.id,
                "mimetype": "application/pdf",
            }
        )
        shipment.label_attachment_id = attachment
        template = self.env.ref(
            "mrw_shipping_connector.mail_template_mrw_pickup_label_ready"
        )

        with patch.object(type(template), "send_mail", return_value=False) as send_mail:
            notification = notification_model.send_customer_notification(
                shipment, "pickup_label_ready", partner.email
            )

        self.assertEqual(notification.state, "sent")
        self.assertEqual(notification.attachment_id, attachment)
        self.assertEqual(send_mail.call_args.kwargs["email_values"]["attachment_ids"], [(4, attachment.id)])
