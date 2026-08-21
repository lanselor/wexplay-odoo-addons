from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .mrw_shipping_constants import ENVIRONMENT_SELECTION


class MrwShippingConfig(models.Model):
    _name = "mrw.shipping.config"
    _description = "Configuración de envíos MRW"
    _order = "company_id, name"

    name = fields.Char(string="Nombre", required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    warehouse_ref = fields.Char(
        string="Referencia de almacén / delegación",
        help="Optional generic reference. It does not depend on Odoo Inventory.",
    )
    environment = fields.Selection(
        selection=ENVIRONMENT_SELECTION,
        string="Entorno",
        required=True,
        default="test",
    )
    test_wsdl_url = fields.Char(
        string="URL WSDL pruebas",
        required=True,
        default="https://sagec-test.mrw.es/MRWEnvio.asmx?WSDL",
    )
    production_wsdl_url = fields.Char(
        string="URL WSDL producción",
        required=True,
        default="https://sagec.mrw.es/MRWEnvio.asmx?WSDL",
    )
    api_timeout_seconds = fields.Integer(
        string="Timeout SOAP (segundos)",
        default=90,
        required=True,
        help=(
            "Tiempo máximo de espera para llamadas SOAP de negocio contra MRW. "
            "La generación de etiquetas en producción puede tardar más que el "
            "WSDL de diagnóstico."
        ),
    )
    tracking_wsdl_url = fields.Char(
        string="URL WSDL de seguimiento",
        required=True,
        default="http://seguimiento.mrw.es/swc/wssgmntnvs.asmx?WSDL",
        help="Servicio SOAP MRW independiente para consultar el seguimiento nacional.",
    )
    enable_tracking_queries = fields.Boolean(
        string="Permitir consultas de seguimiento",
        default=False,
        help="Activa las consultas manuales de tracking. No modifica el estado de Odoo.",
    )
    last_tracking_connection_test_at = fields.Datetime(
        string="Última prueba de tracking",
        readonly=True,
        copy=False,
    )
    last_tracking_connection_test_status = fields.Selection(
        selection=[("success", "Correcto"), ("error", "Error")],
        string="Estado última prueba de tracking",
        readonly=True,
        copy=False,
    )
    last_tracking_connection_test_message = fields.Text(
        string="Mensaje última prueba de tracking",
        readonly=True,
        copy=False,
    )
    agency_code = fields.Char(string="Código de franquicia", required=True)
    subscriber_code = fields.Char(string="Código de abonado", required=True)
    department_code = fields.Char(string="Código de departamento")
    username = fields.Char(string="Usuario", required=True, copy=False)
    password = fields.Char(
        string="Contraseña",
        required=True,
        copy=False,
        groups="mrw_shipping_connector.group_mrw_shipping_administrator",
    )
    default_national_service_id = fields.Many2one(
        comodel_name="mrw.shipping.service",
        string="Servicio nacional por defecto",
        domain="[('active', '=', True), ('service_type', 'in', ('national', 'both'))]",
        ondelete="restrict",
    )
    default_international_service_id = fields.Many2one(
        comodel_name="mrw.shipping.service",
        string="Servicio internacional por defecto",
        domain="[('active', '=', True), ('service_type', 'in', ('international', 'both'))]",
        ondelete="restrict",
    )
    enable_international_shipments = fields.Boolean(
        string="Permitir envíos internacionales",
        help=(
            "Activa las operaciones SOAP internacionales de MRW. Mantener "
            "desactivado hasta validar TransmEnvioInternacional y "
            "EtiquetaEnvioInternacional con la cuenta MRW actual."
        ),
    )
    enable_production_calls = fields.Boolean(
        string="Permitir llamadas reales de producción",
        help=(
            "Activa llamadas SOAP contra el entorno de producción de MRW. "
            "Mantener desactivado hasta completar la validación en pruebas y "
            "tener autorización operativa para emitir envíos reales."
        ),
    )
    notification_shipment_created_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Plantilla de envío creado",
        domain="[('model_id.model', '=', 'mrw.shipping.shipment')]",
        ondelete="restrict",
        help="Plantilla usada al comunicar el número y el enlace de seguimiento.",
    )
    notification_pickup_label_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Plantilla de etiqueta de recogida",
        domain="[('model_id.model', '=', 'mrw.shipping.shipment')]",
        ondelete="restrict",
        help="Plantilla usada al enviar al cliente la etiqueta PDF de una recogida.",
    )
    is_default = fields.Boolean(string="Por defecto", default=False)
    last_connection_test_at = fields.Datetime(
        string="Última prueba de conexión",
        readonly=True,
        copy=False,
    )
    last_connection_test_status = fields.Selection(
        selection=[
            ("success", "Correcto"),
            ("error", "Error"),
        ],
        string="Estado última prueba de conexión",
        readonly=True,
        copy=False,
    )
    last_connection_test_message = fields.Text(
        string="Mensaje última prueba de conexión",
        readonly=True,
        copy=False,
    )
    last_wsdl_inspection_at = fields.Datetime(
        string="Última inspección WSDL",
        readonly=True,
        copy=False,
    )
    last_wsdl_inspection_status = fields.Selection(
        selection=[
            ("success", "Correcto"),
            ("error", "Error"),
        ],
        string="Estado última inspección WSDL",
        readonly=True,
        copy=False,
    )
    last_wsdl_inspection_message = fields.Text(
        string="Mensaje última inspección WSDL",
        readonly=True,
        copy=False,
    )
    last_wsdl_operation_count = fields.Integer(
        string="Número de operaciones WSDL",
        readonly=True,
        copy=False,
    )
    last_wsdl_operations = fields.Text(
        string="Operaciones WSDL",
        readonly=True,
        copy=False,
    )
    last_wsdl_operation_details = fields.Text(
        string="Detalle de operaciones WSDL",
        readonly=True,
        copy=False,
    )
    last_diagnostic_at = fields.Datetime(
        string="Último diagnóstico",
        readonly=True,
        copy=False,
    )
    last_diagnostic_status = fields.Selection(
        selection=[
            ("success", "Correcto"),
            ("warning", "Aviso"),
            ("error", "Error"),
        ],
        string="Estado último diagnóstico",
        readonly=True,
        copy=False,
    )
    last_diagnostic_message = fields.Text(
        string="Resumen último diagnóstico",
        readonly=True,
        copy=False,
    )
    last_diagnostic_report = fields.Text(
        string="Informe último diagnóstico",
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        (
            "name_company_uniq",
            "unique(name, company_id)",
            "The MRW configuration name must be unique per company.",
        ),
    ]

    @api.constrains("is_default", "company_id")
    def _check_single_default_per_company(self):
        for config in self:
            if not config.is_default:
                continue
            domain = [
                ("id", "!=", config.id),
                ("company_id", "=", config.company_id.id),
                ("is_default", "=", True),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    _("Only one default MRW configuration is allowed per company.")
                )

    @api.constrains(
        "environment",
        "test_wsdl_url",
        "production_wsdl_url",
        "api_timeout_seconds",
        "default_national_service_id",
        "default_international_service_id",
    )
    def _check_configuration_values(self):
        for config in self:
            if config.environment == "test" and not config.test_wsdl_url:
                raise ValidationError(_("The test WSDL URL is required."))
            if config.environment == "production" and not config.production_wsdl_url:
                raise ValidationError(_("The production WSDL URL is required."))
            if not 5 <= config.api_timeout_seconds <= 300:
                raise ValidationError(
                    _("The MRW SOAP timeout must be between 5 and 300 seconds.")
                )
            config._check_default_service_type()

    def _check_default_service_type(self):
        self.ensure_one()
        national_service = self.default_national_service_id
        if national_service and national_service.service_type not in ("national", "both"):
            raise ValidationError(
                _("The default national service must be national or both.")
            )
        international_service = self.default_international_service_id
        if international_service and international_service.service_type not in (
            "international",
            "both",
        ):
            raise ValidationError(
                _("The default international service must be international or both.")
            )

    def _get_wsdl_url(self):
        self.ensure_one()
        if self.environment == "production":
            return self.production_wsdl_url
        return self.test_wsdl_url

    def _prepare_auth_header(self):
        self.ensure_one()
        return {
            "CodigoFranquicia": self.agency_code or "",
            "CodigoAbonado": self.subscriber_code or "",
            "CodigoDepartamento": self.department_code or "",
            "UserName": self.username or "",
            "Password": self.password or "",
        }

    def action_test_connection(self):
        result = False
        for config in self:
            result = config._test_wsdl_connection()
        return result

    def action_test_tracking_connection(self):
        result = False
        for config in self:
            result = config._test_tracking_wsdl_connection()
        return result

    def action_inspect_wsdl(self):
        result = False
        for config in self:
            result = config._inspect_wsdl()
        return result

    def action_run_diagnostic(self):
        result = False
        for config in self:
            result = config._run_diagnostic_suite()
        return result

    def _test_wsdl_connection(self):
        self.ensure_one()
        wsdl_url = self._get_wsdl_url()
        started_at = fields.Datetime.now()
        try:
            content = self._fetch_wsdl(wsdl_url)
            self._check_wsdl_content(content)
        except (HTTPError, URLError, TimeoutError, ValueError) as error:
            self.write(
                {
                    "last_connection_test_at": started_at,
                    "last_connection_test_status": "error",
                    "last_connection_test_message": str(error),
                }
            )
            self._create_connection_log("test_connection", "error", str(error))
            return self._notification(_("MRW WSDL connection failed."), str(error), "danger")
        message = _("WSDL connection successful: %s") % wsdl_url
        self.write(
            {
                "last_connection_test_at": started_at,
                "last_connection_test_status": "success",
                "last_connection_test_message": message,
            }
        )
        self._create_connection_log("test_connection", "success", message)
        return self._notification(_("MRW WSDL connection successful."), message, "success")

    def _test_tracking_wsdl_connection(self):
        self.ensure_one()
        started_at = fields.Datetime.now()
        try:
            content = self._fetch_wsdl(self.tracking_wsdl_url)
            self._check_wsdl_content(content)
            operations = self._extract_wsdl_operations(content)
            expected_operation = "SeguimientoNumeroEnvioMRWNacional"
            if expected_operation not in operations:
                raise ValueError(
                    _("The tracking WSDL does not expose %s.") % expected_operation
                )
        except (HTTPError, URLError, TimeoutError, ElementTree.ParseError, ValueError) as error:
            self.write(
                {
                    "last_tracking_connection_test_at": started_at,
                    "last_tracking_connection_test_status": "error",
                    "last_tracking_connection_test_message": str(error),
                }
            )
            self._create_connection_log("test_tracking_connection", "error", str(error))
            return self._notification(
                _("MRW tracking connection failed."), str(error), "danger"
            )
        message = _("MRW tracking WSDL connection successful: %s") % self.tracking_wsdl_url
        self.write(
            {
                "last_tracking_connection_test_at": started_at,
                "last_tracking_connection_test_status": "success",
                "last_tracking_connection_test_message": message,
            }
        )
        self._create_connection_log("test_tracking_connection", "success", message)
        return self._notification(_("MRW tracking connection successful."), message, "success")

    def _inspect_wsdl(self):
        self.ensure_one()
        wsdl_url = self._get_wsdl_url()
        started_at = fields.Datetime.now()
        try:
            content = self._fetch_wsdl(wsdl_url)
            operations = self._extract_wsdl_operations(content)
            if not operations:
                raise ValueError(_("No SOAP operations were found in the WSDL."))
            operation_details = self._extract_wsdl_operation_details(content)
        except (HTTPError, URLError, TimeoutError, ElementTree.ParseError, ValueError) as error:
            self.write(
                {
                    "last_wsdl_inspection_at": started_at,
                    "last_wsdl_inspection_status": "error",
                    "last_wsdl_inspection_message": str(error),
                    "last_wsdl_operation_count": 0,
                    "last_wsdl_operations": False,
                    "last_wsdl_operation_details": False,
                }
            )
            self._create_connection_log("inspect_wsdl", "error", str(error))
            return self._notification(_("MRW WSDL inspection failed."), str(error), "danger")
        operations_text = "\n".join(operations)
        message = _("Found %s SOAP operations.") % len(operations)
        self.write(
            {
                "last_wsdl_inspection_at": started_at,
                "last_wsdl_inspection_status": "success",
                "last_wsdl_inspection_message": message,
                "last_wsdl_operation_count": len(operations),
                "last_wsdl_operations": operations_text,
                "last_wsdl_operation_details": operation_details,
            }
        )
        self._create_connection_log(
            "inspect_wsdl",
            "success",
            message,
            operation_details or operations_text,
        )
        return self._notification(_("MRW WSDL inspection successful."), message, "success")

    def _run_diagnostic_suite(self):
        self.ensure_one()
        started_at = fields.Datetime.now()
        lines = []
        severity = "success"
        expected_operations = {
            "TransmEnvio": {"TransmEnvio"},
            "Etiqueta": {"GetEtiquetaEnvio", "EtiquetaEnvio"},
            "CancelarEnvio": {"CancelarEnvio"},
        }

        def add_line(status, label, detail):
            lines.append("[%s] %s: %s" % (status.upper(), label, detail))

        try:
            self._check_default_service_type()
        except ValidationError as error:
            add_line("error", "Servicios por defecto", str(error))
            severity = "error"
        else:
            add_line("ok", "Servicios por defecto", "La configuracion es coherente.")

        missing_auth = [
            label
            for label, value in (
                ("CodigoFranquicia", self.agency_code),
                ("CodigoAbonado", self.subscriber_code),
                ("UserName", self.username),
                ("Password", self.password),
            )
            if not value
        ]
        if missing_auth:
            add_line(
                "error",
                "Credenciales",
                "Faltan campos obligatorios: %s." % ", ".join(missing_auth),
            )
            severity = "error"
        else:
            add_line("ok", "Credenciales", "Cabecera AuthInfo completa.")

        if not self.default_national_service_id:
            add_line(
                "warning",
                "Servicio nacional",
                "No hay servicio nacional por defecto configurado.",
            )
            if severity == "success":
                severity = "warning"
        else:
            add_line(
                "ok",
                "Servicio nacional",
                "Servicio por defecto: %s." % self.default_national_service_id.display_name,
            )

        if self.enable_international_shipments and not self.default_international_service_id:
            add_line(
                "warning",
                "Servicio internacional",
                "Internacional activado sin servicio internacional por defecto.",
            )
            if severity == "success":
                severity = "warning"
        elif self.default_international_service_id:
            add_line(
                "ok",
                "Servicio internacional",
                "Servicio por defecto: %s."
                % self.default_international_service_id.display_name,
            )

        wsdl_url = self._get_wsdl_url()
        try:
            content = self._fetch_wsdl(wsdl_url)
            self._check_wsdl_content(content)
            operations = set(self._extract_wsdl_operations(content))
        except (HTTPError, URLError, TimeoutError, ElementTree.ParseError, ValueError) as error:
            add_line("error", "WSDL", str(error))
            severity = "error"
        else:
            add_line("ok", "WSDL", "Conexion correcta con %s." % wsdl_url)
            missing_operations = []
            for label, accepted_names in expected_operations.items():
                if not (operations & accepted_names):
                    missing_operations.append("%s (%s)" % (label, ", ".join(sorted(accepted_names))))
            if missing_operations:
                add_line(
                    "warning",
                    "Operaciones SOAP",
                    "No aparecen en el WSDL: %s." % ", ".join(missing_operations),
                )
                if severity == "success":
                    severity = "warning"
            else:
                add_line(
                    "ok",
                    "Operaciones SOAP",
                    "Se encontraron las operaciones esperadas para envio, etiqueta y cancelacion.",
                )

        summary = {
            "success": _("Diagnostic completed successfully."),
            "warning": _("Diagnostic completed with warnings."),
            "error": _("Diagnostic completed with errors."),
        }[severity]
        report = "\n".join(lines)
        self.write(
            {
                "last_diagnostic_at": started_at,
                "last_diagnostic_status": severity,
                "last_diagnostic_message": summary,
                "last_diagnostic_report": report,
            }
        )
        self._create_connection_log(
            "run_diagnostic",
            "success" if severity != "error" else "error",
            summary,
            report,
        )
        notification_type = {
            "success": "success",
            "warning": "warning",
            "error": "danger",
        }[severity]
        return self._notification(_("MRW diagnostic finished."), summary, notification_type)

    def _fetch_wsdl(self, wsdl_url):
        request = Request(
            wsdl_url,
            headers={"User-Agent": "Odoo MRW Shipping Connector"},
        )
        with urlopen(request, timeout=15) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise ValueError(_("Unexpected HTTP status: %s") % status)
            return response.read(1024 * 1024)

    def _check_wsdl_content(self, content):
        if not content:
            raise ValueError(_("The WSDL response is empty."))
        lowered = content.lower()
        if b"definitions" not in lowered and b"wsdl" not in lowered:
            raise ValueError(_("The response does not look like a WSDL document."))

    def _extract_wsdl_operations(self, content):
        root = ElementTree.fromstring(content)
        operations = []
        seen = set()
        for node in root.iter():
            if self._local_name(node.tag) != "operation":
                continue
            operation_name = node.attrib.get("name")
            if not operation_name or operation_name in seen:
                continue
            seen.add(operation_name)
            operations.append(operation_name)
        return sorted(operations)

    def _extract_wsdl_operation_details(self, content):
        root = ElementTree.fromstring(content)
        details = {}
        for node in root.iter():
            if self._local_name(node.tag) != "operation":
                continue
            operation_name = node.attrib.get("name")
            if not operation_name:
                continue
            details.setdefault(operation_name, {})
            for child in node:
                child_name = self._local_name(child.tag)
                if child_name == "operation":
                    soap_action = child.attrib.get("soapAction")
                    if soap_action:
                        details[operation_name]["soapAction"] = soap_action
                elif child_name in ("input", "output"):
                    message = child.attrib.get("message")
                    if message:
                        details[operation_name][child_name] = message
        lines = []
        for operation_name in sorted(details):
            values = details[operation_name]
            lines.append(operation_name)
            if values.get("soapAction"):
                lines.append("  soapAction: %s" % values["soapAction"])
            if values.get("input"):
                lines.append("  input: %s" % values["input"])
            if values.get("output"):
                lines.append("  output: %s" % values["output"])
        return "\n".join(lines)

    def _local_name(self, tag):
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag

    def _create_connection_log(self, operation, status, message, response_raw=False):
        self.env["mrw.shipping.log"].sudo().create(
            {
                "config_id": self.id,
                "operation": operation,
                "status": status,
                "mrw_message": message if status == "success" else False,
                "error_message": message if status == "error" else False,
                "response_raw": response_raw,
                "user_id": self.env.user.id,
            }
        )

    def _notification(self, title, message, notification_type):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notification_type,
                "sticky": False,
            },
        }
