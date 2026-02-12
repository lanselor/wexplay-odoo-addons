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

    # Reemplazo robusto: no depende de ir.model
    res_model = fields.Selection(
        selection=[
            ("sale.order", "Sales: Quotation / Order"),
            ("account.move", "Accounting: Invoice"),
            ("repair.order", "Repairs: Repair Order"),
        ],
        string="Applies to",
        required=True,
        index=True,
        help="Used to filter templates by document type (sale.order includes quotations & orders).",
    )

    body = fields.Text(
        string="Message Body",
        required=True,
        help="Template text. Rendering will be implemented in the wizard iteration.",
    )
