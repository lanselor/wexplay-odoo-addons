from datetime import datetime, time, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class WexPurchaseListLine(models.Model):
    _name = "wex_purchase_list.line"
    _description = "Wexplay Purchase List Line"
    _order = "create_date desc, id desc"
    _rec_name = "name"

    _RESERVATION_NOTIFICATION_DELAY_DAYS = 1
    _RESERVATION_REQUEST_DELAY_DAYS = 3

    name = fields.Char(
        string="Display Name",
        compute="_compute_name",
        store=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )

    requested_by = fields.Many2one(
        "res.users",
        string="Requested by",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )

    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        index=True,
        ondelete="restrict",
    )

    quantity = fields.Float(
        string="Quantity",
        default=1.0,
        required=True,
    )

    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        domain=[("supplier_rank", ">", 0)],
        required=True,
        index=True,
    )

    vendor_url = fields.Char(
        string="Vendor URL"
    )

    vendor_link_html = fields.Html(
        string="Vendor Link",
        compute="_compute_vendor_link_html",
        sanitize=False,
        readonly=True,
    )

    customer_price_note = fields.Monetary(
        currency_field="currency_id",
        help="Precio informado al cliente (referencia).",
    )

    is_reservation = fields.Boolean()
    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        ondelete="restrict",
        index=True,
    )
    allow_reservation_without_customer = fields.Boolean(
        string="Permitir repuesto sin cliente seleccionado",
        help="Excepción operativa para permitir una reserva sin cliente identificado.",
    )
    customer_notified = fields.Boolean()
    customer_notified_by = fields.Many2one(
        "res.users",
        string="Notified By",
        readonly=True,
        copy=False,
        index=True,
    )
    requested_on = fields.Date(
        string="Requested On",
        required=True,
        default=fields.Date.context_today,
        readonly=True,
        copy=False,
        index=True,
    )
    received_on = fields.Datetime(
        string="Received On",
        readonly=True,
        copy=False,
        index=True,
    )
    customer_notified_on = fields.Datetime(
        string="Customer Notified On",
        readonly=True,
        copy=False,
        index=True,
    )

    reservation_status = fields.Selection(
        [
            ("normal", "Normal"),
            ("reservation", "Reserva"),
        ],
        string="Reserva",
        compute="_compute_reservation_status",
        store=True,
        readonly=True,
    )
    reservation_followup_state = fields.Selection(
        [
            ("not_reservation", "No Reserva"),
            ("waiting_arrival", "Esperando llegada"),
            ("pending_notification", "Pendiente de avisar"),
            ("overdue", "Con retraso"),
            ("notified", "Avisado"),
        ],
        string="Reservation Follow-up",
        compute="_compute_reservation_followup_state",
        store=True,
        readonly=True,
    )
    reservation_board_section = fields.Selection(
        [
            ("pending_notification", "Pendientes de aviso"),
            ("overdue", "Con retraso"),
            ("waiting_arrival", "Esperando llegada"),
            ("notified", "Ya avisadas"),
        ],
        string="Reservation Board Section",
        compute="_compute_reservation_board_section",
        store=True,
        readonly=True,
    )
    is_notification_overdue = fields.Boolean(
        string="Notification Overdue",
        compute="_compute_reservation_deadlines",
        search="_search_is_notification_overdue",
        readonly=True,
    )
    is_request_overdue = fields.Boolean(
        string="Request Overdue",
        compute="_compute_reservation_deadlines",
        search="_search_is_request_overdue",
        readonly=True,
    )
    days_since_request = fields.Integer(
        string="Days Since Request",
        compute="_compute_reservation_deadlines",
        readonly=True,
    )
    days_pending_notification = fields.Integer(
        string="Days Pending Notification",
        compute="_compute_reservation_deadlines",
        readonly=True,
    )

    notes = fields.Text()

    state = fields.Selection(
        [
            ("draft_wait_customer", "Espera de Confirmación"),
            ("to_purchase", "Pendiente de compra"),
            ("ordered", "Pedido"),
            ("received", "Recibido"),
            ("cancelled", "Cancelado"),
        ],
        default="draft_wait_customer",
        required=True,
        index=True,
    )

    purchase_order_id = fields.Many2one(
        "purchase.order",
        readonly=True,
        copy=False,
        index=True,
    )

    purchase_order_line_id = fields.Many2one(
        "purchase.order.line",
        readonly=True,
        copy=False,
        index=True,
    )

    # ORÍGENES
    repair_id = fields.Many2one(
        "repair.order",
        ondelete="set null",
        index=True,
    )

    repair_part_move_id = fields.Many2one(
        "stock.move",
        ondelete="set null",
        index=True,
    )

    sale_line_id = fields.Many2one(
        "sale.order.line",
        string="Línea de venta",
        ondelete="set null",
        index=True,
    )

    @api.depends("product_id", "repair_id", "sale_line_id")
    def _compute_name(self):
        for rec in self:
            product_name = rec.product_id.display_name or _("Línea de compra")
            origin = rec.repair_id.display_name or rec.sale_line_id.order_id.name or False
            rec.name = f"{product_name} · {origin}" if origin else product_name

    @api.depends("is_reservation")
    def _compute_reservation_status(self):
        for rec in self:
            rec.reservation_status = "reservation" if rec.is_reservation else "normal"

    @api.depends(
        "is_reservation",
        "state",
        "customer_notified",
        "is_notification_overdue",
        "is_request_overdue",
    )
    def _compute_reservation_followup_state(self):
        for rec in self:
            if not rec.is_reservation:
                rec.reservation_followup_state = "not_reservation"
            elif rec.customer_notified:
                rec.reservation_followup_state = "notified"
            elif rec.is_notification_overdue or rec.is_request_overdue:
                rec.reservation_followup_state = "overdue"
            elif rec.state == "received":
                rec.reservation_followup_state = "pending_notification"
            else:
                rec.reservation_followup_state = "waiting_arrival"

    @api.depends("reservation_followup_state", "is_reservation")
    def _compute_reservation_board_section(self):
        for rec in self:
            if not rec.is_reservation:
                rec.reservation_board_section = False
            elif rec.reservation_followup_state == "overdue":
                rec.reservation_board_section = "overdue"
            elif rec.reservation_followup_state == "pending_notification":
                rec.reservation_board_section = "pending_notification"
            elif rec.reservation_followup_state == "notified":
                rec.reservation_board_section = "notified"
            else:
                rec.reservation_board_section = "waiting_arrival"

    @api.depends("is_reservation", "customer_notified", "requested_on", "received_on", "state")
    def _compute_reservation_deadlines(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_since_request = rec._get_days_since_date(rec.requested_on, today)
            rec.days_pending_notification = rec._get_days_since_datetime(rec.received_on, today)
            rec.is_notification_overdue = rec._is_notification_overdue(today=today)
            rec.is_request_overdue = rec._is_request_overdue(today=today)

    @api.depends("vendor_url")
    def _compute_vendor_link_html(self):
        for rec in self:
            if rec.vendor_url:
                rec.vendor_link_html = (
                    '<a href="%s" target="_blank" class="wex_vendor_link_button" '
                    'title="%s" aria-label="%s">'
                    '<span class="wex_vendor_link_icon">↗</span>'
                    '<span class="wex_vendor_link_text">%s</span>'
                    "</a>"
                ) % (
                    rec.vendor_url,
                    _("Open vendor link"),
                    _("Open vendor link"),
                    _("Open"),
                )
            else:
                rec.vendor_link_html = False

    def _get_days_since_date(self, date_value, today):
        if not date_value:
            return 0
        return max((today - date_value).days, 0)

    def _get_days_since_datetime(self, datetime_value, today):
        if not datetime_value:
            return 0
        return self._get_days_since_date(fields.Datetime.to_datetime(datetime_value).date(), today)

    def _is_notification_overdue(self, *, today):
        self.ensure_one()
        if not self.is_reservation or self.customer_notified or self.state != "received" or not self.received_on:
            return False
        received_date = fields.Datetime.to_datetime(self.received_on).date()
        deadline = received_date + timedelta(days=self._RESERVATION_NOTIFICATION_DELAY_DAYS)
        return today > deadline

    def _is_request_overdue(self, *, today):
        self.ensure_one()
        if not self.is_reservation or self.customer_notified or not self.requested_on:
            return False
        deadline = self.requested_on + timedelta(days=self._RESERVATION_REQUEST_DELAY_DAYS)
        return today > deadline

    def _get_overdue_domain(self, field_name, delay_days):
        today = fields.Date.context_today(self)
        deadline = today - timedelta(days=delay_days)
        deadline_value = deadline
        if field_name == "received_on":
            deadline_value = fields.Datetime.to_string(datetime.combine(deadline, time.max))
        return [
            ("is_reservation", "=", True),
            ("customer_notified", "=", False),
            (field_name, "!=", False),
            (field_name, "<=", deadline_value),
        ]

    def _search_is_notification_overdue(self, operator, value):
        value = bool(value)
        if operator not in ("=", "!="):
            raise UserError(_("Unsupported search on notification overdue."))
        domain = self._get_overdue_domain("received_on", self._RESERVATION_NOTIFICATION_DELAY_DAYS)
        return domain if (operator == "=" and value) or (operator == "!=" and not value) else ["!"] + domain

    def _search_is_request_overdue(self, operator, value):
        value = bool(value)
        if operator not in ("=", "!="):
            raise UserError(_("Unsupported search on request overdue."))
        domain = self._get_overdue_domain("requested_on", self._RESERVATION_REQUEST_DELAY_DAYS)
        return domain if (operator == "=" and value) or (operator == "!=" and not value) else ["!"] + domain

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            self._apply_reservation_defaults(vals)
            self._apply_customer_notified_tracking(vals, now)
            self._apply_received_tracking(vals, now)
        records = super().create(vals_list)
        records._validate_reservation_requirements()
        return records

    def write(self, vals):
        vals = dict(vals)
        now = fields.Datetime.now()
        self._apply_origin_customer_defaults(vals)
        self._apply_reservation_defaults(vals)
        self._apply_customer_notified_tracking(vals, now)
        self._apply_received_tracking(vals, now)
        result = super().write(vals)
        self._validate_reservation_requirements()
        return result

    def _apply_customer_notified_tracking(self, vals, now):
        if "customer_notified" not in vals:
            return
        vals["customer_notified_on"] = now if vals["customer_notified"] else False
        vals["customer_notified_by"] = self.env.user.id if vals["customer_notified"] else False

    def _apply_received_tracking(self, vals, now):
        if vals.get("state") == "received" and "received_on" not in vals:
            vals["received_on"] = now

    def _apply_reservation_defaults(self, vals):
        if vals.get("is_reservation") is False:
            vals.setdefault("allow_reservation_without_customer", False)
            vals.setdefault("customer_notified", False)
        elif vals.get("is_reservation"):
            vals.setdefault("allow_reservation_without_customer", False)

    def _apply_origin_customer_defaults(self, vals):
        if not vals.get("is_reservation") or vals.get("customer_id") or len(self) != 1:
            return
        customer = self._get_origin_customer()
        if customer:
            vals["customer_id"] = customer.id
            vals.setdefault("allow_reservation_without_customer", False)

    def _get_origin_customer(self):
        self.ensure_one()
        if self.repair_id and self.repair_id.partner_id:
            return self.repair_id.partner_id
        if self.sale_line_id and self.sale_line_id.order_id.partner_id:
            return self.sale_line_id.order_id.partner_id
        return self.env["res.partner"]

    def _validate_reservation_requirements(self):
        for rec in self:
            if not rec.is_reservation:
                continue
            if not rec.customer_id and not rec.allow_reservation_without_customer:
                raise ValidationError(_(
                    "Las reservas requieren un cliente, salvo que se marque la excepción "
                    "'Permitir repuesto sin cliente seleccionado'."
                ))

    @api.constrains("is_reservation", "customer_id", "allow_reservation_without_customer")
    def _check_reservation_customer_requirement(self):
        self._validate_reservation_requirements()

    def _check_can_mark_customer_notified(self):
        for line in self:
            if not line.is_reservation:
                raise UserError(_("Solo las reservas pueden marcarse como avisadas."))
            if line.state != "received":
                raise UserError(_("Solo puedes avisar al cliente cuando el repuesto ya ha llegado."))
            if not line.customer_id:
                raise UserError(_("No puedes marcar como avisada una reserva que sigue sin cliente."))

    def _get_customer_notification_message(self):
        self.ensure_one()
        customer_name = self.customer_id.display_name if self.customer_id else _("Sin cliente")
        return _(
            "Cliente avisado desde Lista de compra.<br/>"
            "<b>Producto:</b> %(product)s<br/>"
            "<b>Cliente:</b> %(customer)s"
        ) % {
            "product": self.product_id.display_name,
            "customer": customer_name,
        }

    def _post_customer_notified_message(self):
        for line in self:
            message = line._get_customer_notification_message()
            if line.repair_id and hasattr(line.repair_id, "message_post"):
                line.repair_id.message_post(body=message)
            elif line.sale_line_id and line.sale_line_id.order_id and hasattr(line.sale_line_id.order_id, "message_post"):
                line.sale_line_id.order_id.message_post(body=message)

    def action_mark_customer_notified(self):
        self._check_can_mark_customer_notified()
        pending_lines = self.filtered(lambda line: not line.customer_notified)
        if pending_lines:
            pending_lines.write({"customer_notified": True})
            pending_lines._post_customer_notified_message()
        return True

    def _get_whatsapp_notification_target(self):
        self.ensure_one()
        if self.repair_id:
            return "repair.order", self.repair_id.id
        if self.sale_line_id and self.sale_line_id.order_id:
            return "sale.order", self.sale_line_id.order_id.id
        if self.customer_id:
            return "res.partner", self.customer_id.id
        raise UserError(_("Selecciona un cliente antes de abrir WhatsApp."))

    def action_open_customer_whatsapp(self):
        self.ensure_one()
        if "whatsapp.compose.wizard" not in self.env.registry.models:
            raise UserError(_("El módulo Wex WhatsApp Chatter no está instalado."))

        res_model, res_id = self._get_whatsapp_notification_target()
        return {
            "type": "ir.actions.act_window",
            "name": _("Redactar WhatsApp"),
            "res_model": "whatsapp.compose.wizard",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_res_model": res_model,
                "default_res_id": res_id,
            },
        }

    def action_mark_as_received(self, received_on=None):
        timestamp = received_on or fields.Datetime.now()
        self.filtered(lambda line: line.state == "ordered").write({
            "state": "received",
            "received_on": timestamp,
        })
        return True

    @api.onchange("product_id")
    def _onchange_product_id_autofill_vendor(self):
        """
        Al crear/editar líneas manualmente desde la lista:
        - Autocompleta proveedor (primer seller válido) si no está puesto
        - Autocompleta URL desde el producto si existe y no está puesta
        """
        for rec in self:
            if not rec.product_id:
                continue

            if not rec.vendor_url:
                rec.vendor_url = rec._get_vendor_url_for_product(rec.product_id) or rec.vendor_url
            if not rec.vendor_id:
                rec.vendor_id = rec._get_optional_vendor_for_product(rec.product_id) or rec.vendor_id

    @api.onchange("is_reservation")
    def _onchange_is_reservation_set_customer(self):
        for rec in self:
            if rec.is_reservation and not rec.customer_id:
                rec.customer_id = rec._get_origin_customer()

    def _user_is_manager(self):
        return self.env.user.has_group("wex_purchase_list.group_wex_purchase_list_manager")

    def _check_can_create_rfqs(self):
        if not self._user_is_manager():
            raise UserError(_("Solo los managers pueden generar RFQ desde la lista de compra."))

    @api.model
    def _build_add_result(self, line, mode, message):
        return {
            "line": line,
            "mode": mode,
            "message": message,
        }

    @api.model
    def _get_valid_product_for_purchase_list(self, product_id):
        if not product_id:
            raise UserError(_("No se puede añadir a la lista de compra: falta Producto."))
        product = self.env["product.product"].browse(product_id).exists()
        if not product:
            raise UserError(_("No se puede añadir a la lista de compra: el producto no existe."))
        if product.type == "service":
            raise UserError(_("No se pueden añadir servicios a la lista de compra."))
        return product

    @api.model
    def _check_requested_quantity(self, qty):
        if not qty or qty <= 0:
            raise UserError(_("No se puede añadir a la lista de compra: la Cantidad debe ser mayor que cero."))

    @api.model
    def _get_optional_vendor_for_product(self, product):
        sellers = product.seller_ids
        if not sellers:
            return False
        vendor = sellers[0].partner_id
        return vendor if vendor and vendor.supplier_rank > 0 else False

    @api.model
    def _get_default_vendor_for_product(self, product):
        sellers = product.seller_ids
        if not sellers:
            raise UserError(_("El producto no tiene proveedores configurados."))
        vendor = sellers[0].partner_id
        if not vendor or vendor.supplier_rank <= 0:
            raise UserError(_("El proveedor no es válido."))
        return vendor

    @api.model
    def _get_vendor_url_for_product(self, product):
        template = product.product_tmpl_id
        return getattr(template, "wex_vendor_url", False) if template else False

    @api.model
    def _get_origin_record(self, origin_model, origin_id):
        origin = self.env[origin_model].browse(origin_id).exists()
        if not origin:
            raise UserError(_("No se ha podido determinar el origen para añadir a la lista de compra."))
        return origin

    @api.model
    def _get_customer_vals_from_origin(self, origin_model, origin):
        if origin_model == "stock.move":
            repair = origin.repair_id
            partner = getattr(repair, "partner_id", False)
            return {
                "customer_id": partner.id if partner else False,
                "allow_reservation_without_customer": False,
            }
        if origin_model == "sale.order.line":
            order = origin.order_id
            return {
                "customer_id": order.partner_id.id if order and order.partner_id else False,
                "allow_reservation_without_customer": False,
            }
        return {}

    @api.model
    def _prepare_reservation_vals(self, origin_model, origin):
        vals = {"is_reservation": False}
        if origin_model == "sale.order.line":
            vals["is_reservation"] = True
        elif origin_model == "stock.move":
            vals["is_reservation"] = bool(getattr(origin, "wex_is_reservation", False))
        vals.update(self._get_customer_vals_from_origin(origin_model, origin))
        return vals

    @api.model
    def _prepare_base_line_vals(self, *, company, product, qty, vendor, vendor_url, state):
        return {
            "company_id": company.id,
            "requested_by": self.env.user.id,
            "product_id": product.id,
            "quantity": qty,
            "vendor_id": vendor.id,
            "vendor_url": vendor_url or False,
            "state": state,
        }

    @api.model
    def _check_sale_line_not_already_added(self, sale_line):
        if sale_line.purchase_list_line_id:
            raise UserError(_("Esta línea ya está en la lista de compra."))

    @api.model
    def _add_from_sale_order_line(self, sale_line, *, product, qty, vendor, vendor_url, state):
        self._check_sale_line_not_already_added(sale_line)
        company = sale_line.order_id.company_id or self.env.company
        vals = self._prepare_base_line_vals(
            company=company,
            product=product,
            qty=qty,
            vendor=vendor,
            vendor_url=vendor_url,
            state=state,
        )
        vals.update(self._prepare_reservation_vals("sale.order.line", sale_line))
        vals["sale_line_id"] = sale_line.id
        line = self.create(vals)
        sale_line.purchase_list_line_id = line.id
        return self._build_add_result(line, "created", _("Producto añadido a la lista de compra."))

    @api.model
    def _check_stock_move_not_already_added(self, move):
        if move.purchase_list_line_id and move.purchase_list_line_id.state not in ("cancelled", "received"):
            raise UserError(_("Esta pieza ya está en la lista de compra."))

    @api.model
    def _get_repair_from_move(self, move):
        repair = move.repair_id
        if not repair:
            raise UserError(_("No se ha podido determinar la reparación asociada."))
        return repair

    @api.model
    def _get_mergeable_repair_line(self, repair, product):
        return self.search(
            [
                ("repair_id", "=", repair.id),
                ("product_id", "=", product.id),
                ("state", "not in", ("cancelled", "received")),
            ],
            limit=1,
        )

    @api.model
    def _merge_into_existing_repair_line(self, existing_line, move, qty, vendor_url):
        existing_line.quantity += qty
        if vendor_url and not existing_line.vendor_url:
            existing_line.vendor_url = vendor_url
        existing_line._sync_from_stock_move_reservation(move)
        move.purchase_list_line_id = existing_line.id
        return self._build_add_result(
            existing_line,
            "merged",
            _("La cantidad se ha sumado a una línea existente de la lista de compra."),
        )

    @api.model
    def _add_from_stock_move(self, move, *, product, qty, vendor, vendor_url, state):
        self._check_stock_move_not_already_added(move)
        repair = self._get_repair_from_move(move)
        existing_line = self._get_mergeable_repair_line(repair, product)
        if existing_line:
            return self._merge_into_existing_repair_line(existing_line, move, qty, vendor_url)
        company = repair.company_id or self.env.company
        vals = self._prepare_base_line_vals(
            company=company,
            product=product,
            qty=qty,
            vendor=vendor,
            vendor_url=vendor_url,
            state=state,
        )
        vals.update(self._prepare_reservation_vals("stock.move", move))
        vals.update({
            "repair_id": repair.id,
            "repair_part_move_id": move.id,
        })
        line = self.create(vals)
        move.purchase_list_line_id = line.id
        return self._build_add_result(
            line,
            "created",
            _("Producto añadido a la lista de la compra correctamente."),
        )

    @api.model
    def _get_single_variant_from_template(self, template):
        variants = template.product_variant_ids
        if not variants:
            raise UserError(_("La plantilla no tiene variantes de producto."))
        if len(variants) != 1:
            raise UserError(_(
                "Este producto tiene varias variantes. "
                "Abre una variante concreta y añádela desde ahí."
            ))
        return variants[0]

    @api.model
    def _add_from_product_template(self, template, *, qty, vendor, vendor_url, state):
        variant = self._get_single_variant_from_template(template)
        vals = self._prepare_base_line_vals(
            company=self.env.company,
            product=variant,
            qty=qty,
            vendor=vendor,
            vendor_url=vendor_url,
            state=state,
        )
        line = self.create(vals)
        return self._build_add_result(line, "created", _("Producto añadido a la lista de compra."))

    # ------------------------------------------------------------
    # Centralized creation logic (single source of truth)
    # ------------------------------------------------------------
    @api.model
    def add_from_origin(
        self,
        *,
        origin_model: str,
        origin_id: int,
        product_id: int,
        qty: float,
        state: str = "to_purchase",
    ):
        """
        Centraliza la creación/merge de líneas en wex_purchase_list.line.
        - origin_model/origin_id identifican el origen (sale.order.line, stock.move, etc.)
        - product_id/qty: producto y cantidad solicitada
        - state: estado inicial (por defecto to_purchase)
        Devuelve: dict {line, mode, message}
        """
        self._check_requested_quantity(qty)
        product = self._get_valid_product_for_purchase_list(product_id)
        vendor = self._get_default_vendor_for_product(product)
        vendor_url = self._get_vendor_url_for_product(product)
        origin = self._get_origin_record(origin_model, origin_id)

        if origin_model == "sale.order.line":
            return self._add_from_sale_order_line(
                origin,
                product=product,
                qty=qty,
                vendor=vendor,
                vendor_url=vendor_url,
                state=state,
            )
        if origin_model == "stock.move":
            return self._add_from_stock_move(
                origin,
                product=product,
                qty=qty,
                vendor=vendor,
                vendor_url=vendor_url,
                state=state,
            )
        if origin_model == "product.template":
            return self._add_from_product_template(
                origin,
                qty=qty,
                vendor=vendor,
                vendor_url=vendor_url,
                state=state,
            )
        raise UserError(_("Origen no soportado: %s") % origin_model)

    def _sync_from_stock_move_reservation(self, move):
        self.ensure_one()
        if not move.repair_id:
            return
        partner = getattr(move.repair_id, "partner_id", False)
        vals = {
            "is_reservation": bool(move.wex_is_reservation),
            "customer_id": partner.id if partner else False,
            "allow_reservation_without_customer": False,
        }
        self.write(vals)

    def _check_rfq_lines_selected(self, lines):
        if not lines:
            raise UserError(_("No hay líneas seleccionadas."))

    def _check_rfq_lines_state(self, lines):
        not_ready = lines.filtered(lambda line: line.state != "to_purchase")
        if not_ready:
            raise UserError(_("Solo se pueden crear RFQ desde líneas en estado 'Pendiente de compra'."))

    def _check_rfq_lines_not_linked(self, lines):
        already_linked = lines.filtered(lambda line: line.purchase_order_line_id)
        if already_linked:
            raise UserError(_(
                "Hay líneas ya vinculadas a una RFQ/PO. "
                "Quita esas líneas de la selección o duplica la línea si necesitas pedir de nuevo."
            ))

    def _check_rfq_lines_have_vendor(self, lines):
        missing_vendor = lines.filtered(lambda line: not line.vendor_id)
        if missing_vendor:
            raise UserError(_("El proveedor es obligatorio en todas las líneas."))

    def _check_rfq_selection(self, lines):
        self._check_rfq_lines_selected(lines)
        self._check_rfq_lines_state(lines)
        self._check_rfq_lines_not_linked(lines)
        self._check_rfq_lines_have_vendor(lines)

    def _group_lines_for_rfqs(self, lines):
        groups = {}
        for line in lines:
            company = line.company_id or self.env.company
            key = (company.id, line.vendor_id.id)
            groups.setdefault(key, self.env["wex_purchase_list.line"])
            groups[key] |= line
        return groups

    def _prepare_purchase_order_vals(self, company, vendor):
        return {
            "partner_id": vendor.id,
            "company_id": company.id,
            "origin": _("Wexplay - Lista de compra"),
        }

    def _prepare_purchase_order_line_vals(self, po, line, now):
        company = po.company_id
        product = line.product_id.with_company(company)
        uom = product.uom_po_id or product.uom_id
        price_unit = product.standard_price or 0.0
        vals = {
            "order_id": po.id,
            "product_id": product.id,
            "name": product.display_name,
            "product_qty": line.quantity or 1.0,
            "product_uom": uom.id,
            "price_unit": price_unit,
            "date_planned": now,
        }
        return vals, price_unit

    def _create_purchase_order_for_group(self, company_id, vendor_id):
        company = self.env["res.company"].browse(company_id)
        vendor = self.env["res.partner"].browse(vendor_id)
        po_vals = self._prepare_purchase_order_vals(company, vendor)
        po = self.env["purchase.order"].with_company(company).create(po_vals)
        return po, self.env["purchase.order.line"].with_company(company)

    def _create_purchase_order_line(self, pol_model, po, line, now):
        pol_vals, price_unit = self._prepare_purchase_order_line_vals(po, line, now)
        pol = pol_model.create(pol_vals)
        if price_unit:
            pol.write({"price_unit": price_unit})
        return pol

    def _mark_line_as_ordered(self, line, po, pol):
        line.write({
            "purchase_order_id": po.id,
            "purchase_order_line_id": pol.id,
            "state": "ordered",
        })

    def _get_created_rfq_action(self, created_orders):
        action = self.env.ref("purchase.purchase_rfq").read()[0]
        action["domain"] = [("id", "in", created_orders.ids)]
        action["context"] = {"create": False}
        return action

    def action_create_rfqs(self):
        """
        Crea RFQ(s) agrupadas por proveedor (y compañía) a partir de líneas 'to_purchase'.
        - Requiere vendor_id (required=True)
        - Solo procesa líneas en estado 'to_purchase'
        - Evita duplicados: si ya tiene purchase_order_line_id, no lo procesa
        """
        self._check_can_create_rfqs()
        lines = self
        self._check_rfq_selection(lines)
        groups = self._group_lines_for_rfqs(lines)
        created_orders = self.env["purchase.order"]
        now = fields.Datetime.now()

        for (company_id, vendor_id), group_lines in groups.items():
            po, pol_model = self._create_purchase_order_for_group(company_id, vendor_id)
            for line in group_lines:
                pol = self._create_purchase_order_line(pol_model, po, line, now)
                self._mark_line_as_ordered(line, po, pol)
            created_orders |= po

        return self._get_created_rfq_action(created_orders)

    @api.constrains("vendor_id")
    def _check_vendor_required(self):
        for rec in self:
            if not rec.vendor_id:
                raise ValidationError(_("El proveedor es obligatorio."))
