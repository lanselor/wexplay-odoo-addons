# -*- coding: utf-8 -*-
from odoo import api, fields, models


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

    rendered_body = fields.Text(string="Message", required=True)

    @api.onchange("partner_id")
    def _onchange_partner_id_set_phone_defaults(self):
        for w in self:
            if not w.partner_id:
                continue
            # Prefer mobile, fallback phone
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
