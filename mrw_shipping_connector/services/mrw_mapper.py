import base64
import binascii
from datetime import date
import re
from xml.etree import ElementTree


SENSITIVE_TAGS = (
    "Password",
    "UserName",
    "CodigoAbonado",
    "CodigoFranquicia",
    "EtiquetaFile",
)


def sanitize_payload(payload):
    """Mask known sensitive XML tags in a SOAP payload string."""
    if not payload:
        return payload
    sanitized = str(payload)
    for tag in SENSITIVE_TAGS:
        pattern = rf"(<(?:\w+:)?{tag}>)(.*?)(</(?:\w+:)?{tag}>)"
        sanitized = re.sub(pattern, rf"\1***\3", sanitized, flags=re.DOTALL)
    return sanitized


def is_base64_payload(payload):
    if not payload:
        return False
    if isinstance(payload, str):
        payload_bytes = payload.strip().encode()
    else:
        payload_bytes = bytes(payload).strip()
    if payload_bytes.startswith(b"%PDF"):
        return False
    try:
        decoded = base64.b64decode(payload_bytes, validate=True)
    except (binascii.Error, ValueError):
        return False
    return decoded.startswith(b"%PDF")


def normalize_label_payload(payload):
    """Return PDF bytes from direct PDF or base64 PDF payloads."""
    if payload is None:
        return b""
    if isinstance(payload, str):
        payload_bytes = payload.strip().encode()
    else:
        payload_bytes = bytes(payload).strip()
    if payload_bytes.startswith(b"%PDF"):
        return payload_bytes
    if is_base64_payload(payload_bytes):
        return base64.b64decode(payload_bytes)
    return payload_bytes


class MRWMapper:
    SOAP_ENV_NS = "http://schemas.xmlsoap.org/soap/envelope/"
    MRW_NS = "http://www.mrw.es/"

    def __init__(self, shipment):
        self.shipment = shipment

    def prepare_create_shipment_request(self):
        if self.shipment.shipment_type == "international":
            return {
                "operation": "TransmEnvioInternacional",
                "params": self._prepare_international_request(),
            }
        return {
            "operation": "TransmEnvio",
            "params": self._prepare_national_request(),
        }

    def prepare_label_request(self):
        operation = (
            "EtiquetaEnvioInternacional"
            if self.shipment.shipment_type == "international"
            else "EtiquetaEnvio"
        )
        top_margin = "20" if self.shipment.shipment_type == "international" else "1100"
        left_margin = "20" if self.shipment.shipment_type == "international" else "650"
        return {
            "operation": operation,
            "params": {
                "request": {
                    "NumeroEnvio": self.shipment.mrw_shipment_number or "",
                    "SeparadorNumerosEnvio": "",
                    "FechaInicioEnvio": self._format_date(
                        self.shipment.mrw_effective_shipping_date
                        or self.shipment.shipping_date
                        or date.today()
                    ),
                    "FechaFinEnvio": "",
                    "TipoEtiquetaEnvio": "0",
                    "ReportTopMargin": top_margin,
                    "ReportLeftMargin": left_margin,
                }
            },
        }

    def prepare_create_shipment_soap_preview(self):
        preview = self.prepare_create_shipment_request()
        return self._build_soap_request(
            preview["operation"],
            preview["params"],
            mask_auth=True,
        )

    def prepare_create_shipment_soap_request(self):
        preview = self.prepare_create_shipment_request()
        return self._build_soap_request(
            preview["operation"],
            preview["params"],
            mask_auth=False,
        )

    def prepare_label_soap_preview(self):
        preview = self.prepare_label_request()
        return self._build_soap_request(
            self._get_soap_wrapper_operation(preview["operation"]),
            preview["params"],
            mask_auth=True,
        )

    def prepare_label_soap_request(self):
        preview = self.prepare_label_request()
        return self._build_soap_request(
            self._get_soap_wrapper_operation(preview["operation"]),
            preview["params"],
            mask_auth=False,
        )

    def prepare_cancel_request(self):
        return {
            "operation": "CancelarEnvio",
            "params": {
                "request": {
                    "CancelaEnvio": {
                        "NumeroEnvioOriginal": (
                            self.shipment.mrw_shipment_number or ""
                        ),
                    },
                },
            },
        }

    def prepare_cancel_soap_preview(self):
        preview = self.prepare_cancel_request()
        return self._build_soap_request(
            preview["operation"],
            preview["params"],
            mask_auth=True,
        )

    def prepare_cancel_soap_request(self):
        preview = self.prepare_cancel_request()
        return self._build_soap_request(
            preview["operation"],
            preview["params"],
            mask_auth=False,
        )

    def _prepare_national_request(self):
        shipment = self.shipment
        if shipment.movement_type == "pickup":
            return {
                "request": {
                    "DatosRecogida": self._prepare_pickup_sender_node(),
                    "DatosEntrega": self._prepare_company_recipient_node(),
                    "DatosServicio": self._prepare_national_service_node(),
                }
            }
        request = {
            "DatosEntrega": self._prepare_delivery_recipient_node(),
            "DatosServicio": self._prepare_national_service_node(),
        }
        return {"request": request}

    def _prepare_delivery_recipient_node(self):
        shipment = self.shipment
        return {
            "Direccion": {
                "CodigoDireccion": "",
                "CodigoTipoVia": "",
                "Via": self._prepare_street_name(shipment.street),
                "Numero": self._prepare_street_number(shipment.street),
                "Resto": self._prepare_street_rest(shipment.street, shipment.street2),
                "CodigoPostal": shipment.zip or "",
                "Poblacion": shipment.city or "",
                "CodigoPais": self._prepare_country_code(shipment.country_id),
            },
            "Nif": shipment.recipient_vat or "",
            "Nombre": shipment.recipient_name or "",
            "Telefono": self._format_phone(
                shipment.recipient_phone,
                shipment.country_id,
            )
            or " ",
            "Contacto": "",
            "ALaAtencionDe": "",
            "Horario": self._prepare_default_schedule(),
            "Observaciones": "",
        }

    def _prepare_pickup_sender_node(self):
        shipment = self.shipment
        return {
            "Direccion": {
                "CodigoDireccion": "",
                "CodigoTipoVia": "",
                "Via": self._prepare_street_name(shipment.street),
                "Numero": self._prepare_street_number(shipment.street),
                "Resto": self._prepare_street_rest(shipment.street, shipment.street2),
                "CodigoPostal": shipment.zip or "",
                "Poblacion": shipment.city or "",
                "CodigoPais": self._prepare_country_code(shipment.country_id),
            },
            "Nif": shipment.recipient_vat or "",
            "Nombre": shipment.recipient_name or "",
            "Telefono": self._format_phone(
                shipment.recipient_phone,
                shipment.country_id,
            )
            or " ",
            "Contacto": shipment.recipient_name or "",
            "Horario": self._prepare_default_schedule(),
            "Observaciones": "",
        }

    def _prepare_company_recipient_node(self):
        company_partner = self.shipment.config_id.company_id.partner_id
        return {
            "Direccion": {
                "CodigoDireccion": "",
                "CodigoTipoVia": "",
                "Via": self._prepare_street_name(company_partner.street),
                "Numero": self._prepare_street_number(company_partner.street),
                "Resto": self._prepare_street_rest(
                    company_partner.street,
                    company_partner.street2,
                ),
                "CodigoPostal": company_partner.zip or "",
                "Poblacion": company_partner.city or "",
                "CodigoPais": self._prepare_country_code(company_partner.country_id),
            },
            "Nif": company_partner.vat or "",
            "Nombre": company_partner.name or "",
            "Telefono": self._format_phone(
                company_partner.mobile or company_partner.phone,
                company_partner.country_id,
            )
            or " ",
            "Contacto": company_partner.name or "",
            "ALaAtencionDe": company_partner.name or "",
            "Horario": self._prepare_default_schedule(),
            "Observaciones": "",
        }

    def _prepare_default_schedule(self):
        return {
            "Rangos": {
                "HorarioRangoRequest": {
                    "Desde": "08:00",
                    "Hasta": "18:00",
                }
            }
        }

    def _prepare_national_service_node(self):
        shipment = self.shipment
        return {
            "Fecha": self._format_date(shipment.shipping_date),
            "Referencia": shipment.reference or shipment.name,
            "EnFranquicia": "E" if shipment.delivery_to_franchise else "N",
            "CodigoServicio": shipment.service_id.code,
            "DescripcionServicio": "",
            "Bultos": self._prepare_packages(),
            "NumeroBultos": str(len(shipment.package_ids)),
            "Peso": self._format_decimal(self._total_weight()),
            "EntregaSabado": "S" if shipment.saturday_delivery else "N",
            "Retorno": "S" if shipment.return_enabled else "N",
            "Reembolso": shipment.cash_on_delivery_type or "",
            "ImporteReembolso": self._format_decimal(
                shipment.cash_on_delivery_amount
            )
            if shipment.cash_on_delivery_amount
            else "",
            "Notificaciones": "",
            "TramoHorario": shipment.time_slot or "0",
        }

    def _prepare_international_request(self):
        shipment = self.shipment
        state_name = shipment.state_id.name if shipment.state_id else ""
        return {
            "request": {
                "DatosEntrega": {
                    "Direccion": {
                        "Direccion": self._prepare_full_street(),
                        "CodigoPostal": shipment.zip or "",
                        "Poblacion": shipment.city or "",
                        "Estado": state_name
                        if self._prepare_country_code() in ("USA", "US")
                        else "",
                        "CodigoPais": self._prepare_country_code(shipment.country_id),
                    },
                    "Nif": shipment.recipient_vat or "",
                    "Nombre": shipment.recipient_name or "",
                    "Telefono": self._format_phone(shipment.recipient_phone) or " ",
                },
                "DatosServicio": {
                    "Fecha": self._format_date(shipment.shipping_date),
                    "Referencia": shipment.reference or shipment.name,
                    "CodigoServicio": shipment.service_id.code,
                    "DescripcionServicio": "",
                    "Bultos": self._prepare_packages(),
                    "NumeroBultos": str(len(shipment.package_ids)),
                    "Peso": self._format_decimal(self._total_weight()),
                    "NotificacionSMS": "",
                },
            }
        }

    def _prepare_packages(self):
        packages = []
        for package in self.shipment.package_ids.sorted("sequence"):
            packages.append(
                {
                    "Alto": self._format_dimension(package.height),
                    "Largo": self._format_dimension(package.length),
                    "Ancho": self._format_dimension(package.width),
                    "Dimension": package.dimension_code or "3",
                    "Referencia": package.internal_reference
                    or f"Package {package.sequence}",
                    "Peso": self._format_decimal(package.weight),
                }
            )
        if not packages:
            return ""
        if len(packages) == 1:
            return {"BultoRequest": packages[0]}
        return {"BultoRequest": packages}

    def _prepare_country_code(self, country=False):
        country = country or self.shipment.country_id
        if not country:
            return ""
        if country.code == "ES":
            return "ESP"
        return country.code or ""

    def _prepare_full_street(self):
        return " ".join(
            part for part in [self.shipment.street, self.shipment.street2] if part
        )

    def _prepare_street_name(self, street=False):
        street = street or self.shipment.street or ""
        match = re.match(r"^(.*?)(?:\s+(\d+)\D*)?$", street.strip())
        if not match:
            return street
        return (match.group(1) or street).strip()

    def _prepare_street_number(self, street=False):
        street = street or self.shipment.street or ""
        match = re.search(r"\b(\d+)\b", street)
        return match.group(1) if match else "0"

    def _prepare_street_rest(self, street=False, street2=False):
        street = (street or self.shipment.street or "").strip()
        street2 = (street2 or self.shipment.street2 or "").strip()
        match = re.search(r"\b\d+\b\s*(.*)$", street)
        rest = match.group(1).strip() if match else ""
        return " ".join(part for part in [rest, street2] if part)

    def _total_weight(self):
        return sum(package.weight for package in self.shipment.package_ids)

    def _format_date(self, value):
        if not value:
            return ""
        return value.strftime("%d/%m/%Y")

    def _format_decimal(self, value):
        value = value or 0
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        return text.replace(".", ",")

    def _format_dimension(self, value):
        value = value or 1
        return str(int(round(value)))

    def _format_phone(self, value, country=False):
        if not value:
            return ""
        cleaned = re.sub(r"[\s\-.()]", "", value)
        if (
            self.shipment.shipment_type == "national"
            and self._prepare_country_code(country or self.shipment.country_id) == "ESP"
        ):
            digits = re.sub(r"\D", "", cleaned)
            if len(digits) == 9:
                return digits
            if digits.startswith("0034") and len(digits) == 13:
                return digits[-9:]
            if digits.startswith("34") and len(digits) == 11:
                return digits[-9:]
        return cleaned

    def _build_soap_request(self, operation, params, mask_auth=True):
        ElementTree.register_namespace("SOAP-ENV", self.SOAP_ENV_NS)
        ElementTree.register_namespace("mrw", self.MRW_NS)
        envelope = ElementTree.Element(f"{{{self.SOAP_ENV_NS}}}Envelope")
        header = ElementTree.SubElement(envelope, f"{{{self.SOAP_ENV_NS}}}Header")
        auth = ElementTree.SubElement(header, f"{{{self.MRW_NS}}}AuthInfo")
        auth_header = (
            self._prepare_masked_auth_header()
            if mask_auth
            else self.shipment.config_id._prepare_auth_header()
        )
        for key, value in auth_header.items():
            child = ElementTree.SubElement(auth, f"{{{self.MRW_NS}}}{key}")
            child.text = value

        body = ElementTree.SubElement(envelope, f"{{{self.SOAP_ENV_NS}}}Body")
        operation_node = ElementTree.SubElement(body, f"{{{self.MRW_NS}}}{operation}")
        self._append_xml_payload(operation_node, params)
        xml_bytes = ElementTree.tostring(
            envelope,
            encoding="utf-8",
            xml_declaration=True,
            short_empty_elements=False,
        )
        return xml_bytes.decode("utf-8")

    def _prepare_masked_auth_header(self):
        auth_header = self.shipment.config_id._prepare_auth_header()
        return {
            "CodigoFranquicia": "***" if auth_header.get("CodigoFranquicia") else "",
            "CodigoAbonado": "***" if auth_header.get("CodigoAbonado") else "",
            "CodigoDepartamento": "***"
            if auth_header.get("CodigoDepartamento")
            else "",
            "UserName": "***" if auth_header.get("UserName") else "",
            "Password": "***" if auth_header.get("Password") else "",
        }

    def _append_xml_payload(self, parent, payload):
        if isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(value, list):
                    for item in value:
                        child = ElementTree.SubElement(parent, f"{{{self.MRW_NS}}}{key}")
                        self._append_xml_payload(child, item)
                    continue
                child = ElementTree.SubElement(parent, f"{{{self.MRW_NS}}}{key}")
                self._append_xml_payload(child, value)
            return
        if isinstance(payload, list):
            for item in payload:
                self._append_xml_payload(parent, item)
            return
        parent.text = "" if payload is None else str(payload)

    def _get_soap_wrapper_operation(self, operation):
        wrappers = {
            "EtiquetaEnvio": "GetEtiquetaEnvio",
            "EtiquetaEnvioInternacional": "GetEtiquetaEnvioInternacional",
        }
        return wrappers.get(operation, operation)
