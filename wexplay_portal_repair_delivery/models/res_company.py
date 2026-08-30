# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    x_portal_shipping_notifications_enabled = fields.Boolean(
        string="Avisos automáticos de logística en portal",
        default=False,
        help=(
            "Envía un aviso individual a los usuarios portal autorizados cuando "
            "MRW haya confirmado una recogida o entrega y su etiqueta esté lista."
        ),
    )
