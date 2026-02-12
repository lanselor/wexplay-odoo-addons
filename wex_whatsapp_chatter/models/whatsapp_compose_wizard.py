# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class WhatsappComposeWizard(models.TransientModel):
    _name = "whatsapp.compose.wizard"
    _description = "Compose WhatsApp Message"

    res_model = fields.Selection(
        selection=[
            ("sale.order", "Sales: Quotation / Order"),
            ("account.move", "Accounting: Invoice"),
            ("repair.order", "Repairs: Repair Order"),
        ],
        string="Document Type",
        required=True,
        default="sale.order",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Recipient",
        required=True,
    )

    phone_source = fields.Selection(
        selection=[
            ("mobile", "Mobile"),
            ("phone", "Phone"),
            ("custom", "Custom"),
        ],
        string="Phone source",
        required=True,
        default="mobile",
    )

    phone_number = fields.Char(string="Phone", required=True)

    template_id = fields.Many2one(
        "whatsapp.template",
        string="Template",
        domain="[('res_model', '=', res_model)]",
    )

    sale_order_id = fields.Many2one(
        "sale.order",
        string="Quotation / Order",
    )

    account_move_id = fields.Many2one(
        "account.move",
        string="Invoice",
        domain="[('move_type', 'in', ('out_invoice','out_refund')), ('state', '!=', 'cancel')]",
    )

    portal_url = fields.Char(
        string="Portal URL",
        compute="_compute_portal_url",
        store=False,
    )

    rendered_body = fields.Text(string="Message", required=True)

    @api.onchange("partner_id")
    def _onchange_partner_id_set_phone_defaults(self):
        for w in self:
            if not w.partner_id:
                continue
            if w.partner_id.mobile:
                w.phone_source = "mobile"
                w.phone_number = w.partner_id.mobile
            elif w.partner_id.phone:
                w.phone_source = "phone"
                w.phone_number = w.partner_id.phone

    @api.onchange("phone_source")
    def _onchange_phone_source(self):
        for w in self:
            if not w.partner_id:
                continue
            if w.phone_source == "mobile":
                w.phone_number = w.partner_id.mobile or ""
            elif w.phone_source == "phone":
                w.phone_number = w.partner_id.phone or ""
            # custom: keep existing

    @api.onchange("template_id")
    def _onchange_template_id_set_body(self):
        for w in self:
            if w.template_id:
                # Iteration 2: copy raw body (render with record context comes later)
                w.rendered_body = w.template_id.body or ""

    @api.onchange("res_model")
    def _onchange_res_model_clear_document(self):
        for w in self:
            w.sale_order_id = False
            w.account_move_id = False

    @api.depends("res_model", "sale_order_id", "account_move_id")
    def _compute_portal_url(self):
        for w in self:
            w.portal_url = ""
            if w.res_model == "sale.order" and w.sale_order_id:
                w.portal_url = w.sale_order_id.get_portal_url()
            elif w.res_model == "account.move" and w.account_move_id:
                w.portal_url = w.account_move_id.get_portal_url()

    def action_insert_portal_link(self):
        self.ensure_one()

        if self.res_model not in ("sale.order", "account.move"):
            raise UserError("Portal link is only available for Sales and Invoices.")

        if not self.portal_url:
            raise UserError("Select a document first to generate its portal link.")

        msg = (self.rendered_body or "").rstrip()
        sep = "\n\n" if msg else ""
        self.rendered_body = f"{msg}{sep}{self.portal_url}"

        return {
            "type": "ir.actions.act_window",
            "res_model": "whatsapp.compose.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
