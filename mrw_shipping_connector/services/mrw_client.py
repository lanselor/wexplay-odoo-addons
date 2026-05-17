from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .mrw_exceptions import MRWConnectionError, MRWUnsupportedOperationError
from .mrw_mapper import MRWMapper, sanitize_payload


class MRWClient:
    """Minimal SOAP client for confirmed MRW operations."""

    TIMEOUT = 30

    def __init__(self, config):
        self.config = config

    def create_shipment(self, shipment):
        mapper = MRWMapper(shipment)
        preview = mapper.prepare_create_shipment_request()
        operation = preview["operation"]
        request_xml = mapper.prepare_create_shipment_soap_request()
        response_xml = self._call(operation, request_xml)
        result = self._parse_result(response_xml, f"{operation}Result")
        return {
            "operation": operation,
            "request_xml": sanitize_payload(request_xml),
            "response_xml": sanitize_payload(response_xml),
            "result": result,
        }

    def get_label(self, shipment):
        mapper = MRWMapper(shipment)
        preview = mapper.prepare_label_request()
        operation = preview["operation"]
        request_xml = mapper.prepare_label_soap_request()
        response_xml = self._call(operation, request_xml)
        result_tag = (
            "GetEtiquetaEnvioInternacionalResult"
            if shipment.shipment_type == "international"
            else "GetEtiquetaEnvioResult"
        )
        result = self._parse_result(response_xml, result_tag)
        return {
            "operation": operation,
            "request_xml": sanitize_payload(request_xml),
            "response_xml": sanitize_payload(response_xml),
            "result": result,
        }

    def cancel_shipment(self, shipment):
        mapper = MRWMapper(shipment)
        preview = mapper.prepare_cancel_request()
        operation = preview["operation"]
        request_xml = mapper.prepare_cancel_soap_request()
        response_xml = self._call(operation, request_xml)
        result = self._parse_result(response_xml, "CancelarEnvioResult")
        return {
            "operation": operation,
            "request_xml": sanitize_payload(request_xml),
            "response_xml": sanitize_payload(response_xml),
            "result": result,
        }

    def _call(self, operation, request_xml):
        endpoint = self._get_service_endpoint()
        request = Request(
            endpoint,
            data=request_xml.encode("utf-8"),
            headers={
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": f'"{self._get_soap_action(operation)}"',
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.TIMEOUT) as response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            if body:
                return body
            raise MRWConnectionError(str(error)) from error
        except (URLError, TimeoutError, OSError) as error:
            raise MRWConnectionError(str(error)) from error

    def _get_service_endpoint(self):
        wsdl_url = self.config._get_wsdl_url()
        parts = urlsplit(wsdl_url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))

    def _get_soap_action(self, operation):
        soap_actions = {
            "EtiquetaEnvio": "http://www.mrw.es/GetEtiquetaEnvio",
            "EtiquetaEnvioInternacional": (
                "http://www.mrw.es/GetEtiquetaEnvioInternacional"
            ),
        }
        return soap_actions.get(operation, f"http://www.mrw.es/{operation}")

    def _parse_result(self, response_xml, expected_result_tag):
        try:
            root = ElementTree.fromstring(response_xml)
        except ElementTree.ParseError as error:
            raise MRWConnectionError(
                f"MRW returned a non-parseable SOAP response: {error}"
            ) from error

        result_node = self._find_first_by_local_name(root, expected_result_tag)
        if result_node is None:
            fault = self._find_first_by_local_name(root, "Fault")
            if fault is not None:
                return {
                    "Estado": "0",
                    "Mensaje": self._node_text(fault),
                    "NumeroSolicitud": "",
                    "NumeroEnvio": "",
                }
            raise MRWConnectionError(
                f"MRW SOAP response does not contain {expected_result_tag}."
            )
        return {
            "Estado": self._find_text(result_node, "Estado"),
            "Mensaje": self._find_text(result_node, "Mensaje"),
            "NumeroSolicitud": self._find_text(result_node, "NumeroSolicitud"),
            "NumeroEnvio": self._find_text(result_node, "NumeroEnvio"),
            "EtiquetaFile": self._find_text(result_node, "EtiquetaFile"),
            "Url": self._find_text(result_node, "Url"),
        }

    def _find_text(self, node, local_name):
        found = self._find_first_by_local_name(node, local_name)
        return self._node_text(found) if found is not None else ""

    def _node_text(self, node):
        return "".join(node.itertext()).strip()

    def _find_first_by_local_name(self, node, local_name):
        for element in node.iter():
            if self._local_name(element.tag) == local_name:
                return element
        return None

    def _local_name(self, tag):
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag
