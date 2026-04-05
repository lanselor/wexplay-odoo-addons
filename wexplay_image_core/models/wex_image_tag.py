# -*- coding: utf-8 -*-

from odoo import fields, models


class WexImageTag(models.Model):
    _name = "wex.image.tag"
    _description = "Wex Image Tag"
    _order = "sequence asc, name asc, id asc"

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("wex_image_tag_code_unique", "unique(code)", "The tag code must be unique."),
        ("wex_image_tag_name_unique", "unique(name)", "The tag name must be unique."),
    ]
