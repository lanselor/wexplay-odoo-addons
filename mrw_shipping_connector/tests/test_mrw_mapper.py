import base64
from xml.etree import ElementTree

from odoo.tests.common import TransactionCase

from odoo.addons.mrw_shipping_connector.services.mrw_mapper import (
    MRWMapper,
    normalize_label_payload,
)
from odoo.addons.mrw_shipping_connector.services.mrw_client import MRWClient


class FakeMRWClient(MRWClient):
    def __init__(self, config, response_xml):
        super().__init__(config)
        self.response_xml = response_xml
        self.called_operation = False
        self.called_request_xml = False

    def _call(self, operation, request_xml):
        self.called_operation = operation
        self.called_request_xml = request_xml
        return self.response_xml


class TestMRWMapper(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_es = cls.env.ref("base.es")
        cls.service = cls.env["mrw.shipping.service"].create(
            {
                "name": "Test Bag 19",
                "code": "T0230",
                "service_type": "national",
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
                "default_national_service_id": cls.service.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Alex Prueba",
                "phone": "+34 650 27 94 87",
                "vat": "32837200P",
                "street": "Agra de Bragua 51 Bajo",
                "zip": "15010",
                "city": "A Coruna",
                "country_id": cls.country_es.id,
            }
        )
        cls.env.company.partner_id.write(
            {
                "street": "Rua Wexplay 10",
                "zip": "15001",
                "city": "A Coruna",
                "country_id": cls.country_es.id,
                "phone": "+34 981 00 00 00",
                "vat": "B70410766",
            }
        )

    def _create_shipment(self):
        shipment = self.env["mrw.shipping.shipment"].create(
            {
                "company_id": self.env.company.id,
                "config_id": self.config.id,
                "service_id": self.service.id,
                "shipment_type": "national",
                "partner_id": self.partner.id,
                "recipient_name": self.partner.name,
                "recipient_phone": self.partner.phone,
                "recipient_vat": self.partner.vat,
                "street": self.partner.street,
                "zip": self.partner.zip,
                "city": self.partner.city,
                "country_id": self.country_es.id,
                "reference": "TEST-001",
                "mrw_effective_shipping_date": "2026-05-05",
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
        return shipment

    def test_national_spanish_phone_is_mapped_without_country_prefix(self):
        preview = MRWMapper(self._create_shipment()).prepare_create_shipment_request()

        delivery = preview["params"]["request"]["DatosEntrega"]
        self.assertEqual(delivery["Telefono"], "650279487")

    def test_national_street_remainder_is_mapped_to_resto(self):
        preview = MRWMapper(self._create_shipment()).prepare_create_shipment_request()

        address = preview["params"]["request"]["DatosEntrega"]["Direccion"]
        self.assertEqual(address["Via"], "Agra de Bragua")
        self.assertEqual(address["Numero"], "51")
        self.assertEqual(address["Resto"], "Bajo")

    def test_pickup_uses_customer_as_collection_and_company_as_delivery(self):
        shipment = self._create_shipment()
        shipment.movement_type = "pickup"

        preview = MRWMapper(shipment).prepare_create_shipment_request()
        request = preview["params"]["request"]

        self.assertEqual(preview["operation"], "TransmEnvio")
        self.assertEqual(request["DatosRecogida"]["Nombre"], "Alex Prueba")
        self.assertEqual(
            request["DatosRecogida"]["Direccion"]["CodigoPostal"],
            "15010",
        )
        self.assertEqual(
            request["DatosEntrega"]["Direccion"]["CodigoPostal"],
            "15001",
        )
        self.assertEqual(request["DatosEntrega"]["Telefono"], "981000000")

    def test_pickup_soap_contains_datos_recogida_before_delivery(self):
        shipment = self._create_shipment()
        shipment.movement_type = "pickup"

        xml = MRWMapper(shipment).prepare_create_shipment_soap_preview()

        self.assertIn("<mrw:DatosRecogida>", xml)
        self.assertIn("<mrw:DatosEntrega>", xml)
        self.assertLess(xml.index("<mrw:DatosRecogida>"), xml.index("<mrw:DatosEntrega>"))

    def test_soap_preview_is_well_formed_and_sanitized(self):
        xml = MRWMapper(self._create_shipment()).prepare_create_shipment_soap_preview()

        ElementTree.fromstring(xml)
        self.assertIn("TransmEnvio", xml)
        self.assertNotIn("01400PSWEXP", xml)
        self.assertNotIn("secret", xml)
        self.assertIn("<mrw:Password>***</mrw:Password>", xml)

    def test_label_payload_accepts_direct_pdf_and_base64_pdf(self):
        pdf_payload = b"%PDF-1.4 test"
        base64_payload = base64.b64encode(pdf_payload)

        self.assertEqual(normalize_label_payload(pdf_payload), pdf_payload)
        self.assertEqual(normalize_label_payload(base64_payload), pdf_payload)

    def test_client_parses_create_shipment_response(self):
        response = """
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <TransmEnvioResponse xmlns="http://www.mrw.es/">
                  <TransmEnvioResult>
                    <Estado>1</Estado>
                    <Mensaje>OK</Mensaje>
                    <NumeroSolicitud>REQ1</NumeroSolicitud>
                    <NumeroEnvio>SHIP1</NumeroEnvio>
                  </TransmEnvioResult>
                </TransmEnvioResponse>
              </soap:Body>
            </soap:Envelope>
        """

        result = MRWClient(self.config)._parse_result(response, "TransmEnvioResult")

        self.assertEqual(result["Estado"], "1")
        self.assertEqual(result["Mensaje"], "OK")
        self.assertEqual(result["NumeroSolicitud"], "REQ1")
        self.assertEqual(result["NumeroEnvio"], "SHIP1")

    def test_client_parses_label_response(self):
        response = """
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <GetEtiquetaEnvioResponse xmlns="http://www.mrw.es/">
                  <GetEtiquetaEnvioResult>
                    <Estado>1</Estado>
                    <Mensaje>OK</Mensaje>
                    <EtiquetaFile>JVBERi0xLjQgdGVzdA==</EtiquetaFile>
                  </GetEtiquetaEnvioResult>
                </GetEtiquetaEnvioResponse>
              </soap:Body>
            </soap:Envelope>
        """

        result = MRWClient(self.config)._parse_result(
            response,
            "GetEtiquetaEnvioResult",
        )

        self.assertEqual(result["Estado"], "1")
        self.assertEqual(result["Mensaje"], "OK")
        self.assertEqual(result["EtiquetaFile"], "JVBERi0xLjQgdGVzdA==")

    def test_label_response_is_sanitized_in_logs(self):
        payload = (
            "<GetEtiquetaEnvioResult>"
            "<EtiquetaFile>JVBERi0xLjQgdGVzdA==</EtiquetaFile>"
            "</GetEtiquetaEnvioResult>"
        )

        from odoo.addons.mrw_shipping_connector.services.mrw_mapper import (
            sanitize_payload,
        )

        self.assertIn("<EtiquetaFile>***</EtiquetaFile>", sanitize_payload(payload))

    def test_label_request_uses_mrw_effective_shipping_date(self):
        shipment = self._create_shipment()
        shipment.mrw_shipment_number = "01400F001137"

        preview = MRWMapper(shipment).prepare_label_request()

        self.assertEqual(
            preview["params"]["request"]["FechaInicioEnvio"],
            "05/05/2026",
        )

    def test_label_soap_uses_wsdl_input_element_wrapper(self):
        shipment = self._create_shipment()
        shipment.mrw_shipment_number = "01400F001137"

        xml = MRWMapper(shipment).prepare_label_soap_preview()

        self.assertIn("<mrw:GetEtiquetaEnvio>", xml)
        self.assertNotIn("<mrw:EtiquetaEnvio>", xml)

    def test_cancel_preview_uses_wsdl_request_structure(self):
        shipment = self._create_shipment()
        shipment.mrw_shipment_number = "01400F001137"

        preview = MRWMapper(shipment).prepare_cancel_request()
        xml = MRWMapper(shipment).prepare_cancel_soap_preview()

        self.assertEqual(preview["operation"], "CancelarEnvio")
        self.assertEqual(
            preview["params"]["request"]["CancelaEnvio"][
                "NumeroEnvioOriginal"
            ],
            "01400F001137",
        )
        self.assertIn("<mrw:CancelarEnvio>", xml)
        self.assertIn("<mrw:NumeroEnvioOriginal>01400F001137", xml)

    def test_client_create_shipment_calls_transm_envio(self):
        shipment = self._create_shipment()
        response = """
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <TransmEnvioResponse xmlns="http://www.mrw.es/">
                  <TransmEnvioResult>
                    <Estado>1</Estado>
                    <Mensaje>OK</Mensaje>
                    <NumeroSolicitud>REQ1</NumeroSolicitud>
                    <NumeroEnvio>SHIP1</NumeroEnvio>
                  </TransmEnvioResult>
                </TransmEnvioResponse>
              </soap:Body>
            </soap:Envelope>
        """
        client = FakeMRWClient(self.config, response)

        result = client.create_shipment(shipment)

        self.assertEqual(client.called_operation, "TransmEnvio")
        self.assertIn("<mrw:TransmEnvio>", client.called_request_xml)
        self.assertEqual(result["result"]["NumeroEnvio"], "SHIP1")
        self.assertNotIn("01400PSWEXP", result["request_xml"])

    def test_client_get_label_calls_etiqueta_with_get_wrapper(self):
        shipment = self._create_shipment()
        shipment.mrw_shipment_number = "01400F001137"
        response = """
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <GetEtiquetaEnvioResponse xmlns="http://www.mrw.es/">
                  <GetEtiquetaEnvioResult>
                    <Estado>1</Estado>
                    <Mensaje>OK</Mensaje>
                    <EtiquetaFile>JVBERi0xLjQgdGVzdA==</EtiquetaFile>
                  </GetEtiquetaEnvioResult>
                </GetEtiquetaEnvioResponse>
              </soap:Body>
            </soap:Envelope>
        """
        client = FakeMRWClient(self.config, response)

        result = client.get_label(shipment)

        self.assertEqual(client.called_operation, "EtiquetaEnvio")
        self.assertIn("<mrw:GetEtiquetaEnvio>", client.called_request_xml)
        self.assertEqual(result["result"]["Estado"], "1")
        self.assertIn("<EtiquetaFile>***</EtiquetaFile>", result["response_xml"])

    def test_client_soap_actions_match_wsdl(self):
        client = MRWClient(self.config)

        self.assertEqual(
            client._get_soap_action("TransmEnvio"),
            "http://www.mrw.es/TransmEnvio",
        )
        self.assertEqual(
            client._get_soap_action("EtiquetaEnvio"),
            "http://www.mrw.es/GetEtiquetaEnvio",
        )
        self.assertEqual(
            client._get_soap_action("CancelarEnvio"),
            "http://www.mrw.es/CancelarEnvio",
        )

    def test_client_cancel_shipment_calls_cancelar_envio(self):
        shipment = self._create_shipment()
        shipment.mrw_shipment_number = "01400F001137"
        response = """
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <CancelarEnvioResponse xmlns="http://www.mrw.es/">
                  <CancelarEnvioResult>
                    <Estado>1</Estado>
                    <Mensaje>Cancelado</Mensaje>
                    <NumeroSolicitud>REQ-CANCEL</NumeroSolicitud>
                    <NumeroEnvio>01400F001137</NumeroEnvio>
                  </CancelarEnvioResult>
                </CancelarEnvioResponse>
              </soap:Body>
            </soap:Envelope>
        """
        client = FakeMRWClient(self.config, response)

        result = client.cancel_shipment(shipment)

        self.assertEqual(client.called_operation, "CancelarEnvio")
        self.assertIn("<mrw:CancelarEnvio>", client.called_request_xml)
        self.assertIn("<mrw:NumeroEnvioOriginal>", client.called_request_xml)
        self.assertEqual(result["result"]["Estado"], "1")
        self.assertEqual(result["result"]["NumeroSolicitud"], "REQ-CANCEL")

    def test_cancellation_rejection_restores_previous_state(self):
        shipment = self._create_shipment()
        shipment.write(
            {
                "state": "label_ready",
                "mrw_shipment_number": "01400F001137",
            }
        )
        response = """
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
              <soap:Body>
                <CancelarEnvioResponse xmlns="http://www.mrw.es/">
                  <CancelarEnvioResult>
                    <Estado>0</Estado>
                    <Mensaje>1) El estado del pedido ya no permite cancelaciones</Mensaje>
                    <NumeroEnvio>01400F001137</NumeroEnvio>
                  </CancelarEnvioResult>
                </CancelarEnvioResponse>
              </soap:Body>
            </soap:Envelope>
        """
        original_client = (
            "odoo.addons.mrw_shipping_connector.models."
            "mrw_shipping_shipment.MRWClient"
        )

        class RejectedCancellationClient(FakeMRWClient):
            def __init__(self, config):
                super().__init__(config, response)

        with self.mock_client(original_client, RejectedCancellationClient):
            shipment.action_request_external_cancellation()

        self.assertEqual(shipment.state, "label_ready")
        self.assertIn("no permite cancelaciones", shipment.last_error)

    def test_config_diagnostic_reports_success_with_expected_operations(self):
        wsdl = b"""
            <definitions xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/">
              <portType name="MRWEnvioSoap">
                <operation name="TransmEnvio"/>
                <operation name="GetEtiquetaEnvio"/>
                <operation name="CancelarEnvio"/>
              </portType>
            </definitions>
        """

        from unittest.mock import patch

        with patch.object(type(self.config), "_fetch_wsdl", return_value=wsdl):
            action = self.config.action_run_diagnostic()

        self.assertEqual(self.config.last_diagnostic_status, "success")
        self.assertIn("TransmEnvio", self.config.last_diagnostic_report)
        self.assertEqual(action["params"]["type"], "success")

    def mock_client(self, target, replacement):
        from unittest.mock import patch

        return patch(target, replacement)
