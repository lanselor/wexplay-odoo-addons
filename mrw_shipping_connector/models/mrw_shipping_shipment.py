import json
import time
import base64
import re
from datetime import datetime
from urllib.parse import quote

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.mrw_shipping_connector.services.mrw_client import MRWClient
from odoo.addons.mrw_shipping_connector.services.mrw_exceptions import MRWError
from odoo.addons.mrw_shipping_connector.services.mrw_mapper import (
    MRWMapper,
    normalize_label_payload,
    sanitize_payload,
)

from .mrw_shipping_constants import (
    CASH_ON_DELIVERY_TYPE_SELECTION,
    SHIPMENT_STATE_SELECTION,
    SHIPMENT_TYPE_SELECTION,
    TIME_SLOT_SELECTION,
)


class MrwShippingShipment(models.Model):
    _name = "mrw.shipping.shipment"
    _description = "Envío MRW"
    _order = "name desc"

    name = fields.Char(
        string="Referencia",
        required=True,
        readonly=True,
        copy=False,
        default="New",
    )
    active = fields.Boolean(string="Activo", default=True)
    state = fields.Selection(
        selection=SHIPMENT_STATE_SELECTION,
        string="Estado",
        required=True,
        default="draft",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    source = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("picking", "Albarán de salida"),
        ],
        string="Origen",
        required=True,
        default="manual",
        readonly=True,
        copy=False,
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Albarán",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    stock_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto esperado",
        copy=False,
        ondelete="restrict",
        help="Producto que Odoo esperará recibir cuando la recogida llegue al almacén.",
    )
    stock_product_uom_qty = fields.Float(
        string="Cantidad esperada",
        default=1.0,
        copy=False,
    )
    stock_product_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unidad de medida",
        related="stock_product_id.uom_id",
        readonly=True,
    )
    carrier_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Transportista",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    config_id = fields.Many2one(
        comodel_name="mrw.shipping.config",
        string="Configuración",
        required=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
        ondelete="restrict",
    )
    service_id = fields.Many2one(
        comodel_name="mrw.shipping.service",
        string="Servicio",
        required=True,
        domain="[('active', '=', True)]",
        ondelete="restrict",
    )
    shipment_type = fields.Selection(
        selection=SHIPMENT_TYPE_SELECTION,
        string="Tipo de envío",
        required=True,
        default="national",
    )
    movement_type = fields.Selection(
        selection=[
            ("delivery", "Entrega al cliente"),
            ("pickup", "Recogida en cliente"),
        ],
        string="Tipo de operación",
        required=True,
        default="delivery",
        help=(
            "Entrega al cliente envía desde la dirección de la compañía "
            "configurada hasta la dirección del cliente. Recogida en cliente "
            "solicita la recogida en la dirección del cliente y la entrega en "
            "la dirección de la compañía configurada."
        ),
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Destinatario",
        required=True,
        ondelete="restrict",
    )
    recipient_name = fields.Char(string="Nombre destinatario", required=True)
    recipient_phone = fields.Char(string="Teléfono destinatario")
    recipient_vat = fields.Char(string="NIF destinatario")
    street = fields.Char(string="Dirección", required=True)
    street2 = fields.Char(string="Dirección 2")
    zip = fields.Char(string="Código postal", required=True)
    city = fields.Char(string="Ciudad", required=True)
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="País",
        required=True,
        ondelete="restrict",
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Provincia/Estado",
        ondelete="restrict",
    )
    reference = fields.Char(
        string="Referencia",
        help=(
            "Internal customer-facing reference. If left empty on manual shipments, "
            "it will be generated automatically from the MRW shipment sequence."
        ),
    )
    shipping_date = fields.Date(
        string="Fecha de envío",
        required=True,
        default=fields.Date.context_today,
    )
    mrw_effective_shipping_date = fields.Date(
        string="Fecha efectiva MRW",
        readonly=True,
        copy=False,
    )
    mrw_shipment_number = fields.Char(
        string="Número de envío MRW",
        readonly=True,
        copy=False,
    )
    mrw_request_number = fields.Char(
        string="Número de solicitud MRW",
        readonly=True,
        copy=False,
    )
    mrw_response_url = fields.Char(string="URL respuesta MRW", readonly=True, copy=False)
    mrw_tracking_status_code = fields.Char(
        string="Código de estado tracking MRW", readonly=True, copy=False
    )
    mrw_tracking_status_description = fields.Char(
        string="Estado tracking MRW", readonly=True, copy=False
    )
    mrw_tracking_last_checked_at = fields.Datetime(
        string="Última consulta de tracking", readonly=True, copy=False
    )
    mrw_tracking_message = fields.Text(
        string="Mensaje tracking MRW", readonly=True, copy=False
    )
    package_ids = fields.One2many(
        comodel_name="mrw.shipping.package",
        inverse_name="shipment_id",
        string="Bultos",
    )
    package_count = fields.Integer(string="Número de bultos", compute="_compute_package_count")
    label_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Etiqueta",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    label_filename = fields.Char(string="Nombre de archivo", readonly=True, copy=False)
    label_mimetype = fields.Char(string="Tipo MIME", readonly=True, copy=False)
    label_generated_at = fields.Datetime(
        string="Fecha de generación de etiqueta",
        readonly=True,
        copy=False,
    )
    last_error = fields.Text(string="Último error", readonly=True, copy=False)
    last_preview_operation = fields.Char(
        string="Última operación previsualizada",
        readonly=True,
        copy=False,
    )
    last_preview_payload = fields.Text(
        string="Payload previsualizado",
        readonly=True,
        copy=False,
    )
    last_preview_soap_xml = fields.Text(
        string="XML SOAP previsualizado",
        readonly=True,
        copy=False,
    )
    last_preview_at = fields.Datetime(
        string="Fecha de previsualización",
        readonly=True,
        copy=False,
    )
    log_count = fields.Integer(string="Logs", compute="_compute_log_count")
    notification_ids = fields.One2many(
        comodel_name="mrw.shipping.notification",
        inverse_name="shipment_id",
        string="Notificaciones al cliente",
        readonly=True,
    )
    notification_count = fields.Integer(
        string="Notificaciones",
        compute="_compute_notification_count",
    )

    delivery_to_franchise = fields.Boolean(string="Entrega en franquicia")
    saturday_delivery = fields.Boolean(string="Entrega en sábado")
    return_enabled = fields.Boolean(string="Retorno")
    cash_on_delivery_type = fields.Selection(
        selection=CASH_ON_DELIVERY_TYPE_SELECTION,
        string="Tipo de reembolso",
    )
    cash_on_delivery_amount = fields.Monetary(string="Importe de reembolso")
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    time_slot = fields.Selection(
        selection=TIME_SLOT_SELECTION,
        string="Tramo horario",
        default="0",
    )

    _sql_constraints = [
        (
            "name_uniq",
            "unique(name)",
            "The shipment reference must be unique.",
        ),
        (
            "mrw_shipment_number_uniq",
            "unique(mrw_shipment_number)",
            "The MRW shipment number must be unique.",
        ),
        (
            "picking_uniq",
            "unique(picking_id)",
            "Only one MRW shipment can be linked to a delivery order.",
        ),
    ]

    @api.depends("package_ids")
    def _compute_package_count(self):
        for shipment in self:
            shipment.package_count = len(shipment.package_ids)

    def _compute_log_count(self):
        grouped = self.env["mrw.shipping.log"].read_group(
            [("shipment_id", "in", self.ids)],
            ["shipment_id"],
            ["shipment_id"],
        )
        counts = {item["shipment_id"][0]: item["shipment_id_count"] for item in grouped}
        for shipment in self:
            shipment.log_count = counts.get(shipment.id, 0)

    def _compute_notification_count(self):
        grouped = self.env["mrw.shipping.notification"].read_group(
            [("shipment_id", "in", self.ids)],
            ["shipment_id"],
            ["shipment_id"],
        )
        counts = {item["shipment_id"][0]: item["shipment_id_count"] for item in grouped}
        for shipment in self:
            shipment.notification_count = counts.get(shipment.id, 0)

    def _get_notification_default_event_type(self):
        self.ensure_one()
        if self.movement_type == "pickup" and self.label_attachment_id:
            return "pickup_label_ready"
        return "shipment_created"

    def action_open_notification_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Enviar correo al cliente"),
            "res_model": "mrw.shipping.notification.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_shipment_id": self.id,
                "default_event_type": self._get_notification_default_event_type(),
            },
        }

    def action_open_notifications(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Notificaciones al cliente"),
            "res_model": "mrw.shipping.notification",
            "view_mode": "list,form",
            "domain": [("shipment_id", "=", self.id)],
            "context": {"default_shipment_id": self.id},
        }

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for shipment in self:
            if shipment.partner_id:
                shipment._apply_partner_snapshot(shipment.partner_id)

    @api.onchange("shipment_type", "config_id")
    def _onchange_default_service_id(self):
        for shipment in self:
            if not shipment.config_id:
                continue
            if shipment.shipment_type == "international":
                shipment.service_id = shipment.config_id.default_international_service_id
            else:
                shipment.service_id = shipment.config_id.default_national_service_id

    @api.constrains("shipment_type", "service_id")
    def _check_service_type(self):
        for shipment in self:
            service_type = shipment.service_id.service_type
            if service_type == "both":
                continue
            if shipment.shipment_type == "national" and service_type != "national":
                raise ValidationError(_("The selected service is not national."))
            if (
                shipment.shipment_type == "international"
                and service_type != "international"
            ):
                raise ValidationError(_("The selected service is not international."))

    @api.constrains("state", "package_ids")
    def _check_ready_requires_packages(self):
        for shipment in self:
            if shipment.state in ("ready", "sent", "label_ready") and not shipment.package_ids:
                raise ValidationError(_("At least one package is required."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("mrw.shipping.shipment")
                    or "New"
                )
            if not vals.get("reference"):
                vals["reference"] = vals["name"]
        shipments = super().create(vals_list)
        for shipment in shipments:
            if shipment.partner_id and not shipment.recipient_name:
                shipment._apply_partner_snapshot(shipment.partner_id)
        return shipments

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if "package_ids" in fields_list and not values.get("package_ids"):
            values["package_ids"] = [
                Command.create(
                    {
                        "sequence": 1,
                        "weight": 1.0,
                        "height": 1.0,
                        "width": 1.0,
                        "length": 1.0,
                        "dimension_code": "3",
                    }
                )
            ]
        return values

    def write(self, vals):
        self._check_write_allowed(vals)
        return super().write(vals)

    def action_prepare(self):
        for shipment in self:
            shipment._check_can_prepare()
            shipment.state = "ready"
            shipment.last_error = False
            shipment._create_log(
                operation="prepare_shipment",
                status="success",
                mrw_message=_("Shipment prepared offline."),
            )

    def action_reset_to_draft(self):
        for shipment in self:
            if shipment.state not in ("ready", "error", "cancelled"):
                raise UserError(_("Only ready, error, or cancelled shipments can be reset."))
            shipment.state = "draft"
            shipment.last_error = False

    def action_cancel_internal(self):
        for shipment in self:
            if shipment.state in ("sent", "label_ready"):
                raise UserError(
                    _(
                        "This shipment has already been sent to MRW. External "
                        "cancellation is not implemented until MRW provides the "
                        "real API operation."
                    )
                )
            shipment.state = "cancelled"

    def action_request_external_cancellation(self):
        result = False
        for shipment in self:
            result = shipment._request_external_cancellation()
        return result

    def action_create_mrw_shipment(self):
        result = False
        for shipment in self:
            result = shipment._send_create_shipment_to_mrw()
        return result

    def action_get_mrw_label(self):
        result = False
        for shipment in self:
            result = shipment._get_label_from_mrw()
        return result

    def action_get_mrw_tracking(self):
        result = False
        for shipment in self:
            result = shipment._get_tracking_from_mrw()
        return result

    def action_extract_mrw_effective_date_from_logs(self):
        result = False
        for shipment in self:
            result = shipment._extract_mrw_effective_date_from_logs()
        return result

    def action_open_label_attachment(self):
        self.ensure_one()
        self._check_label_attachment_exists()
        return {
            "type": "ir.actions.act_window",
            "name": _("Etiqueta MRW"),
            "res_model": "ir.attachment",
            "res_id": self.label_attachment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_tracking_url(self):
        self.ensure_one()
        tracking_url = self._get_tracking_url()
        if not tracking_url:
            raise UserError(_("No MRW tracking link is available yet."))
        return {
            "type": "ir.actions.act_url",
            "url": tracking_url,
            "target": "new",
        }

    def action_download_label_attachment(self):
        self.ensure_one()
        self._check_label_attachment_exists()
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % self.label_attachment_id.id,
            "target": "self",
        }

    def action_open_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Logs técnicos MRW"),
            "res_model": "mrw.shipping.log",
            "view_mode": "list,form",
            "domain": [("shipment_id", "=", self.id)],
            "context": {"default_shipment_id": self.id},
            "target": "current",
        }

    def action_open_stock_picking(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("No hay ningún albarán vinculado."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Albarán"),
            "res_model": "stock.picking",
            "res_id": self.picking_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_create_incoming_picking(self):
        result = False
        for shipment in self:
            shipment._check_can_create_incoming_picking()
            picking = self.env["stock.picking"].create(
                shipment._prepare_incoming_picking_values()
            )
            picking.action_confirm()
            shipment.with_context(allow_picking_link=True).write({"picking_id": picking.id})
            picking.mrw_shipment_id = shipment
            result = shipment.action_open_stock_picking()
        return result

    def action_preview_create_request(self):
        result = False
        for shipment in self:
            shipment._check_can_prepare_preview()
            mapper = MRWMapper(shipment)
            preview = mapper.prepare_create_shipment_request()
            soap_xml = mapper.prepare_create_shipment_soap_preview()
            result = shipment._store_preview(
                "preview_create_shipment",
                preview,
                soap_xml=soap_xml,
            )
        return result

    def action_preview_label_request(self):
        result = False
        for shipment in self:
            if not shipment.mrw_shipment_number:
                raise UserError(_("A MRW shipment number is required to preview labels."))
            mapper = MRWMapper(shipment)
            preview = mapper.prepare_label_request()
            soap_xml = mapper.prepare_label_soap_preview()
            result = shipment._store_preview(
                "preview_label",
                preview,
                soap_xml=soap_xml,
            )
        return result

    def action_preview_cancel_request(self):
        result = False
        for shipment in self:
            if not shipment.mrw_shipment_number:
                raise UserError(
                    _("A MRW shipment number is required to preview cancellation.")
                )
            mapper = MRWMapper(shipment)
            preview = mapper.prepare_cancel_request()
            soap_xml = mapper.prepare_cancel_soap_preview()
            result = shipment._store_preview(
                "preview_cancel_shipment",
                preview,
                soap_xml=soap_xml,
            )
        return result

    def _check_can_prepare(self):
        self.ensure_one()
        missing = []
        if not self.config_id:
            missing.append(_("Configuration"))
        if not self.service_id:
            missing.append(_("Service"))
        if not self.partner_id:
            missing.append(_("Recipient"))
        if not self.package_ids:
            missing.append(_("Packages"))
        if missing:
            raise UserError(_("Missing required data: %s") % ", ".join(missing))
        self._check_pickup_supported()
        if self.state not in ("draft", "error"):
            raise UserError(_("Only draft or error shipments can be prepared."))

    def _check_can_prepare_preview(self):
        self.ensure_one()
        missing = []
        if not self.config_id:
            missing.append(_("Configuration"))
        if not self.service_id:
            missing.append(_("Service"))
        if not self.partner_id:
            missing.append(_("Recipient"))
        if not self.package_ids:
            missing.append(_("Packages"))
        if missing:
            raise UserError(_("Missing required data: %s") % ", ".join(missing))
        self._check_pickup_supported()

    def _check_pickup_supported(self):
        self.ensure_one()
        if self.movement_type != "pickup":
            return
        if self.shipment_type != "national":
            raise UserError(
                _(
                    "La recogida en cliente solo está habilitada para envíos "
                    "nacionales hasta validar el flujo internacional con MRW."
                )
            )
        if not self.recipient_phone:
            raise UserError(_("La recogida en cliente necesita teléfono del cliente."))
        company_partner = self.config_id.company_id.partner_id
        missing = []
        if not company_partner.street:
            missing.append(_("street"))
        if not company_partner.zip:
            missing.append(_("zip"))
        if not company_partner.city:
            missing.append(_("city"))
        if not company_partner.country_id:
            missing.append(_("country"))
        if not (company_partner.mobile or company_partner.phone):
            missing.append(_("phone"))
        if missing:
            raise UserError(
                _(
                    "La recogida en cliente necesita una dirección completa en "
                    "la compañía de la configuración MRW: %s."
                )
                % ", ".join(missing)
            )

    def _check_can_create_incoming_picking(self):
        self.ensure_one()
        if self.movement_type != "pickup":
            raise UserError(
                _("Solo las recogidas en cliente pueden crear albarán entrante.")
            )
        if self.picking_id:
            raise UserError(_("Este envío MRW ya tiene un albarán vinculado."))
        if not self.partner_id:
            raise UserError(_("Indica el cliente antes de crear el albarán."))
        if not self.stock_product_id:
            raise UserError(_("Indica el producto esperado antes de crear el albarán."))
        if self.stock_product_uom_qty <= 0:
            raise UserError(_("La cantidad esperada debe ser mayor que cero."))
        if not self.partner_id.property_stock_customer:
            raise UserError(_("El cliente no tiene ubicación de cliente configurada."))
        self._get_incoming_picking_type()

    def _prepare_incoming_picking_values(self):
        self.ensure_one()
        picking_type = self._get_incoming_picking_type()
        partner = self.partner_id
        product = self.stock_product_id
        source_location = partner.property_stock_customer
        destination_location = picking_type.default_location_dest_id
        return {
            "partner_id": partner.id,
            "picking_type_id": picking_type.id,
            "location_id": source_location.id,
            "location_dest_id": destination_location.id,
            "origin": self.reference or self.name,
            "carrier_id": self.carrier_id.id if self.carrier_id else False,
            "mrw_shipment_id": self.id,
            "move_ids_without_package": [
                Command.create(
                    {
                        "name": product.display_name,
                        "product_id": product.id,
                        "product_uom_qty": self.stock_product_uom_qty,
                        "product_uom": product.uom_id.id,
                        "location_id": source_location.id,
                        "location_dest_id": destination_location.id,
                    }
                )
            ],
        }

    def _get_incoming_picking_type(self):
        self.ensure_one()
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company_id.id)],
            limit=1,
        )
        picking_type = warehouse.in_type_id if warehouse else False
        if not picking_type:
            picking_type = self.env["stock.picking.type"].search(
                [
                    ("code", "=", "incoming"),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
        if not picking_type:
            raise UserError(_("No se encontró un tipo de operación de entrada."))
        if not picking_type.default_location_dest_id:
            raise UserError(
                _("El tipo de operación de entrada no tiene ubicación destino.")
            )
        return picking_type

    def _store_preview(self, operation, preview, soap_xml=False):
        self.ensure_one()
        payload = json.dumps(preview, indent=2, ensure_ascii=False)
        self.write(
            {
                "last_preview_operation": preview.get("operation"),
                "last_preview_payload": payload,
                "last_preview_soap_xml": soap_xml,
                "last_preview_at": fields.Datetime.now(),
            }
        )
        self._create_log(
            operation=operation,
            status="success",
            request_raw=soap_xml or payload,
            mrw_message=_("MRW request preview generated offline."),
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("MRW preview generated."),
                "message": _("The request preview has been stored on the shipment."),
                "type": "success",
                "sticky": False,
            },
        }

    def _send_create_shipment_to_mrw(self):
        self.ensure_one()
        self._check_can_send_to_mrw()
        started = time.monotonic()
        try:
            result = MRWClient(self.config_id).create_shipment(self)
        except MRWError as error:
            duration_ms = int((time.monotonic() - started) * 1000)
            self.write(
                {
                    "state": "error",
                    "last_error": str(error),
                }
            )
            self._create_log(
                operation="create_shipment",
                status="error",
                error_message=str(error),
                duration_ms=duration_ms,
            )
            return self._notify_mrw_result(
                title=_("MRW shipment creation failed."),
                message=str(error),
                notification_type="danger",
            )

        duration_ms = int((time.monotonic() - started) * 1000)
        mrw_result = result["result"]
        mrw_status = str(mrw_result.get("Estado") or "")
        mrw_message = mrw_result.get("Mensaje") or ""
        values = {
            "mrw_request_number": mrw_result.get("NumeroSolicitud") or False,
            "mrw_shipment_number": mrw_result.get("NumeroEnvio") or False,
            "mrw_response_url": mrw_result.get("Url") or False,
            "mrw_effective_shipping_date": self._extract_effective_shipping_date(
                mrw_message
            )
            or self.shipping_date,
        }
        if mrw_status == "1":
            values.update(
                {
                    "state": "sent",
                    "last_error": False,
                }
            )
            log_status = "success"
        else:
            values.update(
                {
                    "state": "error",
                    "last_error": mrw_message
                    or _("MRW rejected the shipment without a message."),
                }
            )
            log_status = "error"
        self.write(values)
        self._create_log(
            operation="create_shipment",
            status=log_status,
            request_raw=result["request_xml"],
            response_raw=result["response_xml"],
            mrw_status=mrw_status,
            mrw_message=mrw_message,
            error_message=False if log_status == "success" else values["last_error"],
            duration_ms=duration_ms,
        )
        if log_status == "error":
            return self._notify_mrw_result(
                title=_("MRW rejected the shipment."),
                message=values["last_error"],
                notification_type="warning",
            )
        return self._notify_mrw_result(
            title=_("MRW shipment created."),
            message=_("MRW shipment number: %s") % (self.mrw_shipment_number or ""),
            notification_type="success",
        )

    def _notify_mrw_result(self, title, message, notification_type):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notification_type,
                "sticky": notification_type != "success",
            },
        }

    def _check_can_send_to_mrw(self):
        self.ensure_one()
        if (
            self.config_id.environment == "production"
            and not self.config_id.enable_production_calls
        ):
            raise UserError(
                _(
                    "Las llamadas reales de producción a MRW están bloqueadas "
                    "en esta configuración."
                )
            )
        if (
            self.shipment_type == "international"
            and not self.config_id.enable_international_shipments
        ):
            raise UserError(
                _(
                    "MRW international shipments are not enabled on this "
                    "configuration. Enable them only after validating the "
                    "international TEST flow with MRW."
                )
            )
        if self.state != "ready":
            raise UserError(_("Only ready shipments can be sent to MRW."))
        if self.mrw_shipment_number:
            raise UserError(
                _(
                    "This shipment already has a MRW shipment number and cannot "
                    "be sent again."
                )
            )
        self._check_can_prepare_preview()

    def _get_label_from_mrw(self):
        self.ensure_one()
        self._check_can_get_label_from_mrw()
        started = time.monotonic()
        try:
            result = MRWClient(self.config_id).get_label(self)
        except MRWError as error:
            duration_ms = int((time.monotonic() - started) * 1000)
            self.write(
                {
                    "last_error": str(error),
                }
            )
            self._create_log(
                operation="get_label",
                status="error",
                error_message=str(error),
                duration_ms=duration_ms,
            )
            return self._notify_mrw_result(
                title=_("MRW label retrieval failed."),
                message=str(error),
                notification_type="danger",
            )

        duration_ms = int((time.monotonic() - started) * 1000)
        mrw_result = result["result"]
        mrw_status = str(mrw_result.get("Estado") or "")
        mrw_message = mrw_result.get("Mensaje") or ""
        if mrw_status != "1":
            error_message = mrw_message or _("MRW rejected the label request.")
            self.write({"last_error": error_message})
            self._create_log(
                operation="get_label",
                status="error",
                request_raw=result["request_xml"],
                response_raw=result["response_xml"],
                mrw_status=mrw_status,
                mrw_message=mrw_message,
                error_message=error_message,
                duration_ms=duration_ms,
            )
            return self._notify_mrw_result(
                title=_("MRW rejected the label request."),
                message=error_message,
                notification_type="warning",
            )

        label_payload = normalize_label_payload(mrw_result.get("EtiquetaFile"))
        if not label_payload:
            error_message = _("MRW accepted the label request but returned no label file.")
            self.write({"last_error": error_message})
            self._create_log(
                operation="get_label",
                status="error",
                request_raw=result["request_xml"],
                response_raw=result["response_xml"],
                mrw_status=mrw_status,
                mrw_message=mrw_message,
                error_message=error_message,
                duration_ms=duration_ms,
            )
            return self._notify_mrw_result(
                title=_("MRW label is empty."),
                message=error_message,
                notification_type="warning",
            )

        attachment = self._store_label_attachment(label_payload)
        self.write(
            {
                "state": "label_ready",
                "label_attachment_id": attachment.id,
                "label_filename": attachment.name,
                "label_mimetype": "application/pdf",
                "label_generated_at": fields.Datetime.now(),
                "last_error": False,
            }
        )
        self._create_log(
            operation="get_label",
            status="success",
            request_raw=result["request_xml"],
            response_raw=result["response_xml"],
            mrw_status=mrw_status,
            mrw_message=mrw_message,
            duration_ms=duration_ms,
        )
        return self._notify_mrw_result(
            title=_("MRW label retrieved."),
            message=_("The MRW label has been attached to the shipment."),
            notification_type="success",
        )

    def _check_can_get_label_from_mrw(self):
        self.ensure_one()
        if (
            self.config_id.environment == "production"
            and not self.config_id.enable_production_calls
        ):
            raise UserError(
                _(
                    "Las llamadas reales de producción a MRW están bloqueadas "
                    "en esta configuración."
                )
            )
        if self.state not in ("sent", "label_ready"):
            raise UserError(_("Only sent shipments can retrieve labels."))
        if not self.mrw_shipment_number:
            raise UserError(_("A MRW shipment number is required to retrieve labels."))

    def _request_external_cancellation(self):
        self.ensure_one()
        self._check_can_request_external_cancellation()
        previous_state = self.state
        self.state = "cancel_pending"
        started = time.monotonic()
        try:
            result = MRWClient(self.config_id).cancel_shipment(self)
        except MRWError as error:
            duration_ms = int((time.monotonic() - started) * 1000)
            self.write(
                {
                    "state": previous_state,
                    "last_error": str(error),
                }
            )
            self._create_log(
                operation="cancel_shipment",
                status="error",
                error_message=str(error),
                duration_ms=duration_ms,
            )
            return self._notify_mrw_result(
                title=_("MRW cancellation failed."),
                message=str(error),
                notification_type="danger",
            )

        duration_ms = int((time.monotonic() - started) * 1000)
        mrw_result = result["result"]
        mrw_status = str(mrw_result.get("Estado") or "")
        mrw_message = mrw_result.get("Mensaje") or ""
        if mrw_status == "1":
            self.write(
                {
                    "state": "cancelled",
                    "last_error": False,
                    "mrw_request_number": mrw_result.get("NumeroSolicitud")
                    or self.mrw_request_number,
                }
            )
            log_status = "success"
            error_message = False
        else:
            error_message = mrw_message or _("MRW rejected the cancellation.")
            self.write(
                {
                    "state": previous_state,
                    "last_error": error_message,
                }
            )
            log_status = "error"
        self._create_log(
            operation="cancel_shipment",
            status=log_status,
            request_raw=result["request_xml"],
            response_raw=result["response_xml"],
            mrw_status=mrw_status,
            mrw_message=mrw_message,
            error_message=error_message,
            duration_ms=duration_ms,
        )
        if log_status == "error":
            return self._notify_mrw_result(
                title=_("MRW rejected the cancellation."),
                message=error_message,
                notification_type="warning",
            )
        return self._notify_mrw_result(
            title=_("MRW shipment cancelled."),
            message=mrw_message or _("The shipment was cancelled in MRW."),
            notification_type="success",
        )

    def _check_can_request_external_cancellation(self):
        self.ensure_one()
        if (
            self.config_id.environment == "production"
            and not self.config_id.enable_production_calls
        ):
            raise UserError(
                _(
                    "Las llamadas reales de producción a MRW están bloqueadas "
                    "en esta configuración."
                )
            )
        if self.state in ("draft", "cancel_pending", "cancelled"):
            raise UserError(
                _(
                    "Only shipments with an active MRW number can request MRW "
                    "cancellation."
                )
            )
        if not self.mrw_shipment_number:
            raise UserError(_("A MRW shipment number is required to cancel."))

    def _check_label_attachment_exists(self):
        self.ensure_one()
        if not self.label_attachment_id:
            raise UserError(_("No MRW label attachment is available."))

    def _get_tracking_from_mrw(self):
        self.ensure_one()
        if not self.config_id.enable_tracking_queries:
            raise UserError(
                _("Enable tracking queries in the MRW configuration before querying MRW.")
            )
        if not self.mrw_shipment_number:
            raise UserError(_("A MRW shipment number is required to query tracking."))
        started = time.monotonic()
        try:
            result = MRWClient(self.config_id).get_tracking(self)
        except MRWError as error:
            duration_ms = int((time.monotonic() - started) * 1000)
            self.write(
                {
                    "mrw_tracking_last_checked_at": fields.Datetime.now(),
                    "mrw_tracking_message": str(error),
                }
            )
            self._create_log(
                operation="get_tracking",
                status="error",
                request_raw=sanitize_payload(getattr(error, "request_raw", False)),
                response_raw=sanitize_payload(getattr(error, "response_raw", False)),
                error_message=str(error),
                duration_ms=duration_ms,
            )
            return self._notify_mrw_result(
                title=_("MRW tracking query failed."),
                message=str(error),
                notification_type="danger",
            )

        duration_ms = int((time.monotonic() - started) * 1000)
        mrw_result = result["result"]
        mrw_status = str(mrw_result.get("Estado") or "")
        mrw_message = mrw_result.get("Mensaje") or ""
        tracking_shipment = mrw_result.get("Envio") or {}
        if mrw_status.lower() not in ("1", "true"):
            error_message = mrw_message or _("MRW rejected the tracking query.")
            self.write(
                {
                    "mrw_tracking_last_checked_at": fields.Datetime.now(),
                    "mrw_tracking_message": error_message,
                }
            )
            self._create_log(
                operation="get_tracking",
                status="error",
                request_raw=result["request_xml"],
                response_raw=result["response_xml"],
                mrw_status=mrw_status,
                mrw_message=mrw_message,
                error_message=error_message,
                duration_ms=duration_ms,
            )
            return self._notify_mrw_result(
                title=_("MRW rejected the tracking query."),
                message=error_message,
                notification_type="warning",
            )

        status_code = tracking_shipment.get("Estado", "")
        status_description = tracking_shipment.get("EstadoDescripcion", "")
        self.write(
            {
                "mrw_tracking_status_code": status_code,
                "mrw_tracking_status_description": status_description,
                "mrw_tracking_last_checked_at": fields.Datetime.now(),
                "mrw_tracking_message": mrw_message,
            }
        )
        self._create_log(
            operation="get_tracking",
            status="success",
            request_raw=result["request_xml"],
            response_raw=result["response_xml"],
            mrw_status=mrw_status,
            mrw_message=mrw_message,
            duration_ms=duration_ms,
        )
        display_status = status_description or status_code or _("No status returned.")
        return self._notify_mrw_result(
            title=_("MRW tracking query successful."),
            message=_("Current MRW status: %s") % display_status,
            notification_type="success",
        )

    def _get_tracking_url(self):
        self.ensure_one()
        if self.picking_id and self.picking_id.carrier_tracking_url:
            return self.picking_id.carrier_tracking_url
        if self.picking_id and self.picking_id.carrier_tracking_ref and self.carrier_id:
            return self.carrier_id.get_tracking_link(self.picking_id)
        if self.mrw_shipment_number:
            return (
                "http://www.mrw.es/seguimiento_envios/"
                "MRW_historico_nacional.asp?enviament=%s"
            ) % quote(self.mrw_shipment_number)
        return False

    def _extract_effective_shipping_date(self, message):
        if not message:
            return False
        matches = re.findall(r"\b(\d{2}/\d{2}/\d{4})\b", message)
        if not matches:
            return False
        try:
            return datetime.strptime(matches[-1], "%d/%m/%Y").date()
        except ValueError:
            return False

    def _extract_mrw_effective_date_from_logs(self):
        self.ensure_one()
        log = self.env["mrw.shipping.log"].search(
            [
                ("shipment_id", "=", self.id),
                ("operation", "=", "create_shipment"),
                ("status", "=", "success"),
                ("mrw_message", "!=", False),
            ],
            order="create_date desc, id desc",
            limit=1,
        )
        effective_date = self._extract_effective_shipping_date(log.mrw_message)
        if effective_date:
            self.mrw_effective_shipping_date = effective_date
            message = _("MRW effective shipping date updated: %s") % effective_date
            notification_type = "success"
        else:
            message = _("No MRW effective shipping date was found in shipment logs.")
            notification_type = "warning"
        return self._notify_mrw_result(
            title=_("MRW effective date check."),
            message=message,
            notification_type=notification_type,
        )

    def _store_label_attachment(self, label_payload):
        self.ensure_one()
        filename = f"{self.mrw_shipment_number or self.name}.pdf"
        res_model = "stock.picking" if self.picking_id else self._name
        res_id = self.picking_id.id if self.picking_id else self.id
        return self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(label_payload),
                "res_model": res_model,
                "res_id": res_id,
                "mimetype": "application/pdf",
            }
        )

    def _check_write_allowed(self, vals):
        if self.env.context.get("allow_picking_link") and set(vals) == {"picking_id"}:
            return
        protected_fields = {
            "config_id",
            "service_id",
            "shipment_type",
            "movement_type",
            "picking_id",
            "carrier_id",
            "partner_id",
            "recipient_name",
            "recipient_phone",
            "recipient_vat",
            "street",
            "street2",
            "zip",
            "city",
            "country_id",
            "state_id",
            "reference",
            "shipping_date",
            "delivery_to_franchise",
            "saturday_delivery",
            "return_enabled",
            "cash_on_delivery_type",
            "cash_on_delivery_amount",
            "time_slot",
        }
        if protected_fields.isdisjoint(vals):
            return
        locked = self.filtered(lambda shipment: shipment.state in ("sent", "label_ready"))
        if locked:
            raise UserError(_("Sent shipments cannot be edited."))

    def _apply_partner_snapshot(self, partner):
        self.ensure_one()
        self.recipient_name = partner.name
        self.recipient_phone = partner.mobile or partner.phone
        self.recipient_vat = partner.vat
        self.street = partner.street
        self.street2 = partner.street2
        self.zip = partner.zip
        self.city = partner.city
        self.country_id = partner.country_id
        self.state_id = partner.state_id

    def _create_log(
        self,
        operation,
        status,
        request_raw=False,
        response_raw=False,
        mrw_status=False,
        mrw_message=False,
        error_message=False,
        duration_ms=0,
    ):
        self.ensure_one()
        return self.env["mrw.shipping.log"].sudo().create(
            {
                "shipment_id": self.id,
                "config_id": self.config_id.id,
                "operation": operation,
                "status": status,
                "request_raw": request_raw,
                "response_raw": response_raw,
                "mrw_status": mrw_status,
                "mrw_message": mrw_message,
                "error_message": error_message,
                "duration_ms": duration_ms,
                "user_id": self.env.user.id,
            }
        )
