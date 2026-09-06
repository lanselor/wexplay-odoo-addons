from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    wex_portal_billing_pending = fields.Boolean(
        string="Pendiente de facturación administrativa", copy=False,
        compute="_compute_portal_billing_visibility", store=True,
        groups="base.group_user", index=True,
    )
    wex_portal_billing_tracked = fields.Boolean(
        string="Seguimiento de facturación activo", copy=False, default=False,
        tracking=True, groups="base.group_user", index=True,
    )
    wex_billing_cancelled_order = fields.Boolean(
        string="Pedido suspendido por cancelación", copy=False, groups="base.group_user",
    )
    wex_billing_tracking_state = fields.Selection([
        ("untracked", "Sin seguimiento"), ("pending", "Pendiente"),
        ("invoiced", "Facturación completada"), ("cancelled", "Pedido cancelado / en revisión"),
        ("manual", "Retirada manual"),
    ], compute="_compute_portal_billing_visibility", store=True,
        string="Seguimiento administrativo", groups="base.group_user", index=True)
    wex_billing_removed_at = fields.Datetime(
        string="Retirado manualmente el", readonly=True, copy=False, groups="base.group_user",
    )
    wex_billing_removed_by = fields.Many2one(
        "res.users", string="Retirado por", readonly=True, copy=False, groups="base.group_user",
    )

    @api.depends(
        "wex_portal_billing_tracked", "wex_billing_cancelled_order", "wex_billing_removed_at",
        "sale_order_id", "sale_order_id.state", "sale_order_id.invoice_status",
        "sale_order_id.order_line.is_downpayment", "sale_order_id.order_line.display_type",
        "sale_order_id.order_line.invoice_lines", "sale_order_id.order_line.invoice_lines.move_id.state",
        "sale_order_id.order_line.invoice_lines.move_id.move_type",
    )
    def _compute_portal_billing_visibility(self):
        for repair in self:
            state = repair._get_portal_billing_tracking_state()
            repair.wex_billing_tracking_state = state
            repair.wex_portal_billing_pending = state == "pending"

    def _get_portal_billing_tracking_state(self):
        self.ensure_one()
        if not self.wex_portal_billing_tracked:
            return "manual" if self.wex_billing_removed_at else "untracked"
        order = self.sale_order_id
        if order.state == "cancel" or (self.wex_billing_cancelled_order and order.state != "sale"):
            return "cancelled"
        if self._is_portal_billing_fully_invoiced():
            return "invoiced"
        return "pending"

    def _is_portal_billing_fully_invoiced(self):
        self.ensure_one()
        order = self.sale_order_id
        if not order or order.state != "sale" or order.invoice_status != "invoiced":
            return False
        lines = order.order_line.filtered(lambda line: not line.display_type and not line.is_downpayment)
        return any(
            invoice_line.move_id.state != "cancel" and invoice_line.move_id.move_type == "out_invoice"
            for invoice_line in lines.invoice_lines
        )

    def action_remove_portal_billing(self):
        self.ensure_one()
        self._check_portal_billing_access()
        self.write({
            "wex_portal_billing_tracked": False,
            "wex_billing_removed_at": fields.Datetime.now(),
            "wex_billing_removed_by": self.env.uid,
        })
        self.message_post(body=_("Retirado manualmente de la bandeja de facturación. Se desactiva su regreso automático."))
        return {"type": "ir.actions.client", "tag": "reload"}

    wex_portal_billing_added_at = fields.Datetime(
        string="Añadido a facturación el", copy=False, readonly=True, groups="base.group_user",
    )
    wex_portal_billing_added_by = fields.Many2one(
        "res.users", string="Añadido por", copy=False, readonly=True, groups="base.group_user",
    )
    wex_billing_partner_id = fields.Many2one(
        "res.partner", related="partner_id.commercial_partner_id", store=True,
        string="Empresa cliente", groups="base.group_user", index=True,
    )
    wex_billing_invoice_status = fields.Selection(
        related="sale_order_id.invoice_status", string="Estado de facturación Odoo",
        groups="base.group_user",
    )
    wex_billing_issue = fields.Char(
        compute="_compute_wex_billing_issue", string="Revisión administrativa", groups="base.group_user",
    )

    @api.depends("sale_order_id", "sale_order_id.state", "sale_order_id.invoice_status")
    def _compute_wex_billing_issue(self):
        for repair in self:
            order = repair.sale_order_id
            if not order:
                repair.wex_billing_issue = _("Falta cotización")
            elif order.state != "sale":
                repair.wex_billing_issue = _("Pedido sin confirmar o cancelado")
            elif order.invoice_status != "to invoice":
                repair.wex_billing_issue = _("Consultar facturas existentes o cantidades facturables")
            else:
                repair.wex_billing_issue = False

    def _check_portal_billing_access(self):
        if not self.env.user.has_group("stock.group_stock_user"):
            raise AccessError(_("Esta acción requiere permisos internos de reparaciones."))
        self.check_access("write")

    def _is_portal_billing_customer(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        return bool(partner.is_company and partner.x_is_professional_sat_customer
                    and partner.wex_has_active_portal)

    def _should_offer_portal_billing(self):
        self.ensure_one()
        is_warranty = self.under_warranty or (
            "x_is_warranty_case" in self._fields and self.x_is_warranty_case
        )
        return bool(self.state == "under_repair" and self.x_budget_stage == "accepted"
                    and not is_warranty and not self.wex_portal_billing_tracked and not self.wex_billing_removed_at
                    and self._is_portal_billing_customer())

    def action_add_portal_billing(self):
        self._check_portal_billing_access()
        for repair in self:
            if not repair._is_portal_billing_customer():
                raise UserError(_("%s: el cliente debe ser una empresa SAT profesional con portal activo.") % repair.display_name)
        for repair in self.filtered(lambda r: not r.wex_portal_billing_tracked):
            repair.write({
                "wex_portal_billing_tracked": True,
                "wex_billing_cancelled_order": repair.sale_order_id.state == "cancel",
                "wex_portal_billing_added_at": fields.Datetime.now(),
                "wex_portal_billing_added_by": self.env.uid,
            })
        return {"type": "ir.actions.client", "tag": "display_notification", "params": {
            "title": _("Facturación administrativa"), "message": _("Seguimiento activado. Los pedidos cancelados o completamente facturados permanecen fuera de pendientes."),
            "type": "success", "next": {"type": "ir.actions.client", "tag": "reload"},
        }}

    def action_repair_end(self):
        self.ensure_one()
        offer = self._should_offer_portal_billing()
        automatic = offer and self.partner_id.commercial_partner_id.wex_auto_portal_billing
        if offer and not automatic and not self.env.context.get("wex_billing_choice_done"):
            return self._open_glue_finish_wizard()
        result = super().action_repair_end()
        if offer and self.state == "done" and (
            automatic or self.env.context.get("wex_billing_add_on_finish")
        ):
            notification = self.action_add_portal_billing()
            if automatic and not isinstance(result, dict):
                return notification
        return result

    def action_create_portal_billing_invoices(self):
        self._check_portal_billing_access()
        if not self or any(not r.wex_portal_billing_pending for r in self):
            raise UserError(_("Selecciona SAT incluidos en la bandeja administrativa."))
        if len(self.mapped("company_id")) != 1 or len(self.mapped("wex_billing_partner_id")) != 1:
            raise UserError(_("Selecciona trabajos de un solo cliente y una sola compañía."))
        for repair in self:
            order = repair.sale_order_id
            if not order or order.state != "sale" or order.invoice_status != "to invoice":
                raise UserError(_("%s: revisa el pedido y sus cantidades facturables antes de continuar.") % repair.display_name)
            if order.company_id != repair.company_id or order.partner_id.commercial_partner_id != repair.wex_billing_partner_id:
                raise UserError(_("%s: el pedido no coincide con el cliente o la compañía del SAT.") % repair.display_name)
        orders = self.mapped("sale_order_id")
        orders.check_access("read")
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_view_sale_advance_payment_inv")
        action["context"] = {
            "active_model": "sale.order", "active_ids": orders.ids, "active_id": orders[:1].id,
            "default_consolidated_billing": True,
            "allowed_company_ids": self.env.companies.ids,
        }
        return action
