# -*- coding: utf-8 -*-

from odoo import fields, models


class WhatsappTemplate(models.Model):
    _name = "whatsapp.template"
    _description = "WhatsApp Template"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        index=True,
    )

    # Explicit model selection (keeps system robust and simple)
    res_model = fields.Selection(
        selection=[
            ("sale.order", "Sales: Quotation / Order"),
            ("account.move", "Accounting: Invoice"),
            ("repair.order", "Repairs: Repair Order"),
            ("res.partner", "Contacts: Contact"),
        ],
        string="Applies to",
        required=True,
        index=True,
        help="Used to filter templates by document type.",
    )

    body = fields.Text(
        string="Message Body",
        required=True,
        help="Supports dynamic variables like ${object.name}, ${object.partner_id.name}, etc.",
    )

    def render_body(self, res_model, res_id):
        """
        Secure dynamic rendering using Odoo's mail.template engine.

        Why:
        - Avoids unsafe eval.
        - Reuses official rendering logic.
        - Supports ${object.field} syntax.

        If no valid record is provided, falls back to raw body.
        """
        self.ensure_one()

        if not (res_model and res_id):
            return self.body or ""

        record = self.env[res_model].browse(res_id).exists()
        if not record:
            return self.body or ""

        rendered = self.env["mail.template"]._render_template(
            self.body or "",
            res_model,
            [record.id],
        )

        return rendered.get(record.id) or (self.body or "")