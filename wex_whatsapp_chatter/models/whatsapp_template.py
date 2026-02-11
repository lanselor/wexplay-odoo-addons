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

    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Applies to Model",
        required=True,
        index=True,
        help="Templates are filtered by the target document model (sale.order, account.move, repair.order, etc.).",
    )

    body = fields.Text(
        string="Message Body",
        required=True,
        help="Template text. Rendering will be implemented in the wizard iteration.",
    )
