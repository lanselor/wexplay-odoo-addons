# -*- coding: utf-8 -*-

from odoo import _, Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class WexRepairShippingOperation(models.Model):
    _name = "wex.repair.shipping.operation"
    _description = "Operación logística SAT"
    _order = "repair_id, operation_type"

    repair_id = fields.Many2one(
        comodel_name="repair.order",
        string="Reparación",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="repair_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        readonly=True,
    )
    repair_requires_shipping = fields.Boolean(
        related="repair_id.x_requires_shipping",
        string="Reparación con logística activa",
        readonly=True,
    )
    operation_type = fields.Selection(
        selection=[
            ("pickup", "Recogida del cliente"),
            ("delivery", "Entrega al cliente"),
        ],
        string="Tipo de operación",
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("picking_ready", "Albarán preparado"),
            ("sent", "Enviado al transportista"),
            ("label_ready", "Etiqueta lista"),
            ("done", "Hecho"),
            ("cancelled", "Cancelado"),
            ("error", "Error"),
        ],
        string="Estado",
        default="draft",
        required=True,
        copy=False,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Dirección del cliente",
        required=True,
        ondelete="restrict",
    )
    carrier_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Transportista",
        check_company=True,
        ondelete="restrict",
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto",
        required=True,
        ondelete="restrict",
    )
    quantity = fields.Float(string="Cantidad", default=1.0, required=True)
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unidad de medida",
        required=True,
    )
    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Albarán",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    mrw_shipment_id = fields.Many2one(
        comodel_name="mrw.shipping.shipment",
        string="Envío MRW",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    tracking_ref = fields.Char(
        string="Referencia de rastreo",
        compute="_compute_tracking_data",
    )
    tracking_url = fields.Char(
        string="URL de seguimiento",
        compute="_compute_tracking_data",
    )
    picking_state = fields.Selection(
        related="picking_id.state",
        string="Estado del albarán",
        readonly=True,
    )
    effective_carrier_id = fields.Many2one(
        related="picking_id.carrier_id",
        string="Transportista aplicado",
        readonly=True,
    )
    label_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Etiqueta",
        compute="_compute_label_attachment_id",
    )
    mrw_state = fields.Selection(
        related="mrw_shipment_id.state",
        string="Estado MRW",
        readonly=True,
    )
    mrw_request_number = fields.Char(
        related="mrw_shipment_id.mrw_request_number",
        string="Número de solicitud MRW",
        readonly=True,
    )
    mrw_shipment_number = fields.Char(
        related="mrw_shipment_id.mrw_shipment_number",
        string="Número de envío MRW",
        readonly=True,
    )
    mrw_last_error = fields.Text(
        related="mrw_shipment_id.last_error",
        string="Último error MRW",
        readonly=True,
    )
    last_error = fields.Text(string="Último error", readonly=True, copy=False)
    invoice_policy = fields.Selection(
        selection=[
            ("sale_if_editable", "Añadir a venta si es editable"),
            ("separate_invoice", "Factura de gastos"),
            ("no_invoice", "No facturar"),
        ],
        string="Facturación",
        default="sale_if_editable",
        required=True,
    )
    charge_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto de gastos",
        domain="[('sale_ok', '=', True)]",
        ondelete="restrict",
    )
    price = fields.Monetary(string="Importe", currency_field="currency_id")
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Factura de gastos",
        readonly=True,
        copy=False,
        ondelete="set null",
    )
    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Línea de venta",
        readonly=True,
        copy=False,
        ondelete="set null",
    )

    _sql_constraints = [
        (
            "repair_operation_type_uniq",
            "unique(repair_id, operation_type)",
            "Cada reparación solo puede tener una recogida y una entrega.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_default_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        if "carrier_id" in vals:
            for operation in self:
                operation._apply_carrier_values(vals)
        return super().write(vals)

    def name_get(self):
        result = []
        labels = dict(self._fields["operation_type"].selection)
        for operation in self:
            operation_label = labels.get(operation.operation_type, _("Operación"))
            repair_name = operation.repair_id.display_name or _("Sin reparación")
            result.append((operation.id, "%s - %s" % (operation_label, repair_name)))
        return result

    @api.onchange("repair_id")
    def _onchange_repair_id(self):
        for operation in self:
            operation._set_defaults_from_repair()

    @api.onchange("carrier_id")
    def _onchange_carrier_id(self):
        for operation in self:
            operation._set_defaults_from_carrier()

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for operation in self:
            if operation.product_id:
                operation.uom_id = operation.product_id.uom_id

    @api.constrains("quantity", "operation_type")
    def _check_operation_values(self):
        for operation in self:
            if operation.quantity <= 0:
                raise ValidationError(_("La cantidad debe ser mayor que cero."))

    @api.depends(
        "picking_id.carrier_tracking_ref",
        "picking_id.carrier_tracking_url",
        "mrw_shipment_id.mrw_shipment_number",
    )
    def _compute_tracking_data(self):
        for operation in self:
            operation.tracking_ref = (
                operation.picking_id.carrier_tracking_ref
                or operation.mrw_shipment_id.mrw_shipment_number
            )
            operation.tracking_url = operation._get_tracking_url()

    @api.depends("picking_id", "mrw_shipment_id.label_attachment_id")
    def _compute_label_attachment_id(self):
        Attachment = self.env["ir.attachment"]
        for operation in self:
            attachment = operation.mrw_shipment_id.label_attachment_id
            if not attachment and operation.picking_id:
                attachment = Attachment.search(
                    [
                        ("res_model", "=", "stock.picking"),
                        ("res_id", "=", operation.picking_id.id),
                        "|",
                        ("mimetype", "=", "application/pdf"),
                        ("name", "ilike", ".pdf"),
                    ],
                    order="create_date desc, id desc",
                    limit=1,
                )
            operation.label_attachment_id = attachment

    def action_create_picking(self):
        for operation in self:
            operation._check_can_create_picking()
            picking = self.env["stock.picking"].create(
                operation._prepare_picking_values()
            )
            picking.action_confirm()
            if operation.operation_type == "delivery":
                picking.action_assign()
            operation.picking_id = picking
            if operation.mrw_shipment_id:
                operation.mrw_shipment_id.with_context(allow_picking_link=True).write(
                    {"picking_id": picking.id}
                )
                picking.mrw_shipment_id = operation.mrw_shipment_id
            operation.state = "picking_ready"
            operation._post_link_message(
                _("Albarán creado"),
                "stock.picking",
                picking.id,
                picking.display_name,
            )
        return self.action_open_picking()

    def action_send_to_carrier(self):
        self.ensure_one()
        self._check_can_send_to_carrier()
        if self.operation_type == "pickup":
            self._send_pickup_to_carrier()
        else:
            self._send_delivery_to_carrier()
        return self.action_open_current_record()

    def action_open_current_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Operación logística"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_picking(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("Todavía no hay albarán."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Albarán"),
            "res_model": "stock.picking",
            "res_id": self.picking_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_mrw_shipment(self):
        self.ensure_one()
        if not self.mrw_shipment_id:
            raise UserError(_("Todavía no hay envío MRW."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Envío MRW"),
            "res_model": "mrw.shipping.shipment",
            "res_id": self.mrw_shipment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_tracking_url(self):
        self.ensure_one()
        tracking_url = self._get_tracking_url()
        if not tracking_url:
            raise UserError(_("Todavía no hay enlace de seguimiento disponible."))
        return {
            "type": "ir.actions.act_url",
            "url": tracking_url,
            "target": "new",
        }

    def action_open_label(self):
        self.ensure_one()
        if not self.label_attachment_id:
            raise UserError(_("Todavía no hay etiqueta disponible."))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=false" % self.label_attachment_id.id,
            "target": "new",
        }

    def action_download_label(self):
        self.ensure_one()
        if not self.label_attachment_id:
            raise UserError(_("Todavía no hay etiqueta disponible."))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % self.label_attachment_id.id,
            "target": "self",
        }

    def _get_tracking_url(self):
        self.ensure_one()
        if self.picking_id and self.picking_id.carrier_tracking_url:
            return self.picking_id.carrier_tracking_url
        if self.picking_id and self.picking_id.carrier_tracking_ref and self.carrier_id:
            return self.carrier_id.get_tracking_link(self.picking_id)
        if self.mrw_shipment_id:
            return self.mrw_shipment_id._get_tracking_url()
        return False

    def action_get_label(self):
        self.ensure_one()
        if self.mrw_shipment_id:
            return self.mrw_shipment_id.action_get_mrw_label()
        if self.picking_id and self.picking_id.mrw_shipment_id:
            self.mrw_shipment_id = self.picking_id.mrw_shipment_id
            return self.picking_id.action_get_mrw_label()
        raise UserError(_("No hay un envío MRW desde el que obtener etiqueta."))

    def action_add_cost_to_sale(self):
        for operation in self:
            operation._check_can_add_cost_to_sale()
            line = self.env["sale.order.line"].create(
                operation._prepare_sale_line_values()
            )
            operation.sale_line_id = line
            operation._post_message(_("Gasto añadido a la venta %s.") % line.order_id.name)
        return True

    def action_create_invoice(self):
        for operation in self:
            operation._check_can_create_invoice()
            invoice = self.env["account.move"].create(operation._prepare_invoice_values())
            operation.invoice_id = invoice
            operation._post_link_message(
                _("Factura de gastos creada"),
                "account.move",
                invoice.id,
                invoice.display_name,
            )
        return self.action_open_invoice()

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("Todavía no hay factura de gastos."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Factura de gastos"),
            "res_model": "account.move",
            "res_id": self.invoice_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _apply_default_values(self, vals):
        repair = self.env["repair.order"].browse(vals.get("repair_id")).exists()
        if repair:
            vals.setdefault("partner_id", repair.partner_id.id)
            vals.setdefault("product_id", repair.product_id.id)
            vals.setdefault("quantity", repair.product_qty or 1.0)
            vals.setdefault(
                "uom_id",
                repair.product_uom.id or repair.product_id.uom_id.id,
            )
        carrier = self.env["delivery.carrier"].browse(vals.get("carrier_id")).exists()
        if carrier:
            vals.setdefault("charge_product_id", carrier.product_id.id)
            vals.setdefault(
                "price",
                carrier.fixed_price or carrier.product_id.lst_price,
            )

    def _apply_carrier_values(self, vals):
        carrier = self.env["delivery.carrier"].browse(vals.get("carrier_id")).exists()
        if not carrier:
            return
        if not vals.get("charge_product_id"):
            vals["charge_product_id"] = carrier.product_id.id
        if not vals.get("price") and not self.price:
            vals["price"] = carrier.fixed_price or carrier.product_id.lst_price

    def _set_defaults_from_repair(self):
        self.ensure_one()
        if not self.repair_id:
            return
        if not self.partner_id:
            self.partner_id = self.repair_id.partner_id
        if not self.product_id:
            self.product_id = self.repair_id.product_id
        if not self.quantity:
            self.quantity = self.repair_id.product_qty or 1.0
        if self.product_id and not self.uom_id:
            self.uom_id = self.repair_id.product_uom or self.product_id.uom_id

    def _set_defaults_from_carrier(self):
        self.ensure_one()
        if not self.carrier_id:
            return
        self.charge_product_id = self.carrier_id.product_id
        if not self.price:
            self.price = self.carrier_id.fixed_price or self.carrier_id.product_id.lst_price

    def _check_can_create_picking(self):
        self.ensure_one()
        if self.picking_id:
            raise UserError(_("Esta operación ya tiene albarán."))
        self._check_common_operation_data()

    def _check_can_send_to_carrier(self):
        self.ensure_one()
        self._check_common_operation_data()
        if self.operation_type == "delivery" and not self.picking_id:
            raise UserError(_("Crea primero el albarán de entrega."))
        if self.operation_type == "delivery" and not self.picking_id.carrier_id:
            raise UserError(_("El albarán no tiene transportista."))
        if self.operation_type == "pickup" and self.mrw_shipment_id:
            raise UserError(_("La recogida ya tiene envío MRW."))
        if self.operation_type == "pickup" and self.carrier_id.delivery_type == "mrw":
            if not self.carrier_id.mrw_config_id or not self.carrier_id.mrw_service_id:
                raise UserError(
                    _("El transportista MRW necesita configuración y servicio MRW.")
                )

    def _check_common_operation_data(self):
        self.ensure_one()
        if not self.repair_id:
            raise UserError(_("Indica la reparación."))
        if not self.repair_requires_shipping:
            raise UserError(_("Activa primero 'Requiere envío / recogida'."))
        if not self.partner_id:
            raise UserError(_("Indica la dirección del cliente."))
        if not self.carrier_id:
            raise UserError(_("Indica el transportista."))
        if not self.product_id:
            raise UserError(_("Indica el producto."))
        if self.quantity <= 0:
            raise UserError(_("La cantidad debe ser mayor que cero."))
        if self.partner_id.type == "contact" and not self.partner_id.street:
            raise UserError(_("La dirección del cliente no tiene calle informada."))
        if self.operation_type == "pickup" or self.carrier_id.delivery_type == "mrw":
            missing = []
            if not self.partner_id.street:
                missing.append(_("calle"))
            if not self.partner_id.zip:
                missing.append(_("código postal"))
            if not self.partner_id.city:
                missing.append(_("ciudad"))
            if not self.partner_id.country_id:
                missing.append(_("país"))
            if not (self.partner_id.mobile or self.partner_id.phone):
                missing.append(_("teléfono"))
            if missing:
                raise UserError(
                    _("La dirección del cliente está incompleta: %s.")
                    % ", ".join(missing)
                )

    def _prepare_picking_values(self):
        self.ensure_one()
        picking_type = self._get_picking_type()
        source_location, dest_location = self._get_picking_locations(picking_type)
        return {
            "partner_id": self.partner_id.id,
            "picking_type_id": picking_type.id,
            "location_id": source_location.id,
            "location_dest_id": dest_location.id,
            "origin": self.repair_id.name,
            "company_id": self.company_id.id,
            "carrier_id": self.carrier_id.id,
            "x_repair_shipping_operation_id": self.id,
            "move_ids": [
                Command.create(
                    {
                        "name": self.product_id.display_name,
                        "product_id": self.product_id.id,
                        "product_uom_qty": self.quantity,
                        "product_uom": self.uom_id.id,
                        "location_id": source_location.id,
                        "location_dest_id": dest_location.id,
                        "company_id": self.company_id.id,
                        "origin": self.repair_id.name,
                    }
                )
            ],
        }

    def _get_picking_type(self):
        self.ensure_one()
        warehouse = self.repair_id.picking_type_id.warehouse_id
        if not warehouse:
            warehouse = self.env["stock.warehouse"].search(
                [("company_id", "=", self.company_id.id)],
                limit=1,
            )
        if self.operation_type == "pickup":
            picking_type = warehouse.in_type_id if warehouse else False
            code = "incoming"
            error = _("No se encontró un tipo de operación de entrada.")
        else:
            picking_type = warehouse.out_type_id if warehouse else False
            code = "outgoing"
            error = _("No se encontró un tipo de operación de salida.")
        if not picking_type:
            picking_type = self.env["stock.picking.type"].search(
                [
                    ("code", "=", code),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
        if not picking_type:
            raise UserError(error)
        return picking_type

    def _get_picking_locations(self, picking_type):
        self.ensure_one()
        if self.operation_type == "pickup":
            source_location = self.partner_id.property_stock_customer
            dest_location = picking_type.default_location_dest_id
        else:
            source_location = (
                self.repair_id.product_location_src_id
                or picking_type.default_location_src_id
            )
            dest_location = self.partner_id.property_stock_customer
        if not source_location or not dest_location:
            raise UserError(_("No se pudieron resolver las ubicaciones del albarán."))
        return source_location, dest_location

    def _send_delivery_to_carrier(self):
        self.ensure_one()
        try:
            self.picking_id.send_to_shipper()
        except Exception as error:
            picking = self.env["stock.picking"].browse(self.picking_id.id)
            if picking.mrw_shipment_id or picking.carrier_tracking_ref:
                self._sync_delivery_state_from_picking()
                self.last_error = str(error)
                self._post_message(
                    _(
                        "MRW created or linked the expedition, but Odoo reported a "
                        "post-send error: %s"
                    )
                    % error
                )
                return
            raise
        self._sync_delivery_state_from_picking()

    def _send_pickup_to_carrier(self):
        self.ensure_one()
        if self.carrier_id.delivery_type != "mrw":
            raise UserError(
                _(
                    "La recogida automática solo está implementada para transportistas MRW."
                )
            )
        shipment = self._create_mrw_pickup_shipment()
        shipment.action_prepare()
        shipment.action_create_mrw_shipment()
        if shipment.state == "error":
            self.write({"state": "error", "last_error": shipment.last_error})
            return
        shipment.action_get_mrw_label()
        self.write(
            {
                "mrw_shipment_id": shipment.id,
                "state": "label_ready" if shipment.label_attachment_id else "sent",
                "last_error": shipment.last_error,
            }
        )

    def _sync_delivery_state_from_picking(self):
        self.ensure_one()
        values = {}
        if self.picking_id.mrw_shipment_id:
            values["mrw_shipment_id"] = self.picking_id.mrw_shipment_id.id
        if self.picking_id.carrier_tracking_ref:
            values["last_error"] = False
            values["state"] = (
                "label_ready" if self.label_attachment_id else "sent"
            )
        elif self.picking_id.mrw_shipment_id and self.picking_id.mrw_shipment_id.last_error:
            values["last_error"] = self.picking_id.mrw_shipment_id.last_error
            values["state"] = "error"
        if values:
            self.write(values)

    def _create_mrw_pickup_shipment(self):
        self.ensure_one()
        package_values = self._prepare_mrw_package_values()
        shipment = self.env["mrw.shipping.shipment"].create(
            {
                "company_id": self.company_id.id,
                "source": "manual",
                "config_id": self.carrier_id.mrw_config_id.id,
                "service_id": self.carrier_id.mrw_service_id.id,
                "carrier_id": self.carrier_id.id,
                "movement_type": "pickup",
                "shipment_type": "national",
                "partner_id": self.partner_id.id,
                "recipient_name": self.partner_id.name,
                "recipient_phone": self.partner_id.mobile or self.partner_id.phone,
                "recipient_vat": self.partner_id.vat,
                "street": self.partner_id.street,
                "street2": self.partner_id.street2,
                "zip": self.partner_id.zip,
                "city": self.partner_id.city,
                "country_id": self.partner_id.country_id.id,
                "state_id": self.partner_id.state_id.id,
                "reference": self.repair_id.name,
                "stock_product_id": self.product_id.id,
                "stock_product_uom_qty": self.quantity,
                "package_ids": [Command.create(package_values)],
            }
        )
        if self.picking_id:
            shipment.with_context(allow_picking_link=True).write(
                {"picking_id": self.picking_id.id}
            )
            self.picking_id.mrw_shipment_id = shipment
        return shipment

    def _prepare_mrw_package_values(self):
        self.ensure_one()
        weight = self.product_id.weight or 1.0
        return {
            "sequence": 1,
            "weight": weight,
            "height": 1,
            "width": 1,
            "length": 1,
            "dimension_code": "3",
            "internal_reference": self.repair_id.name,
        }

    def _check_can_add_cost_to_sale(self):
        self.ensure_one()
        if self.sale_line_id:
            raise UserError(_("El gasto ya está añadido a la venta."))
        if not self.repair_id.sale_order_id:
            raise UserError(_("Esta reparación no tiene venta asociada."))
        posted_invoices = self.repair_id.sale_order_id.invoice_ids.filtered(
            lambda invoice: invoice.state == "posted"
        )
        if posted_invoices:
            raise UserError(
                _(
                    "La venta ya tiene facturas publicadas. Crea una factura de gastos o no factures la operación."
                )
            )
        if self.repair_id.sale_order_id.state not in ("draft", "sent", "sale"):
            raise UserError(_("La venta no está en un estado editable."))
        self._check_charge_data()

    def _check_can_create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            raise UserError(_("Ya existe una factura de gastos."))
        self._check_charge_data()

    def _check_charge_data(self):
        self.ensure_one()
        if not self.charge_product_id:
            raise UserError(_("Indica el producto de gastos."))
        if not self.partner_id:
            raise UserError(_("Indica el cliente."))
        if self.price <= 0:
            raise UserError(_("El importe debe ser mayor que cero."))

    def _prepare_sale_line_values(self):
        self.ensure_one()
        return {
            "order_id": self.repair_id.sale_order_id.id,
            "product_id": self.charge_product_id.id,
            "name": self._get_charge_line_name(),
            "product_uom_qty": 1.0,
            "product_uom": self.charge_product_id.uom_id.id,
            "price_unit": self.price,
        }

    def _prepare_invoice_values(self):
        self.ensure_one()
        return {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_origin": self.repair_id.name,
            "company_id": self.company_id.id,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": self.charge_product_id.id,
                        "name": self._get_charge_line_name(),
                        "quantity": 1.0,
                        "price_unit": self.price,
                    }
                )
            ],
        }

    def _get_charge_line_name(self):
        self.ensure_one()
        return "%s - %s" % (
            self.charge_product_id.display_name,
            dict(self._fields["operation_type"].selection).get(self.operation_type),
        )

    def _post_link_message(self, prefix, model, record_id, display_name):
        self.ensure_one()
        self._post_message(
            "%s: <a href=# data-oe-model='%s' data-oe-id='%s'>%s</a>."
            % (prefix, model, record_id, display_name)
        )

    def _post_message(self, body):
        self.ensure_one()
        self.repair_id.message_post(body=body)
