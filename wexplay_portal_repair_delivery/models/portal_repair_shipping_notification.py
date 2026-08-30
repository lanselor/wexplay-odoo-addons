# -*- coding: utf-8 -*-

from odoo import fields, models


class WexPortalRepairShippingNotification(models.Model):
    _name = "wex.portal.repair.shipping.notification"
    _description = "Aviso portal de logística SAT"
    _order = "create_date desc, id desc"

    operation_id = fields.Many2one(
        comodel_name="wex.repair.shipping.operation",
        string="Operación logística",
        required=True,
        index=True,
        ondelete="cascade",
    )
    repair_id = fields.Many2one(
        related="operation_id.repair_id",
        string="Reparación",
        store=True,
        readonly=True,
    )
    recipient_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario portal",
        required=True,
        index=True,
        ondelete="restrict",
    )
    recipient_email = fields.Char(string="Destinatario", required=True)
    mail_id = fields.Many2one(
        comodel_name="mail.mail",
        string="Correo",
        readonly=True,
        ondelete="set null",
    )
    state = fields.Selection(
        selection=[("queued", "En cola"), ("error", "Error")],
        string="Estado",
        required=True,
        readonly=True,
    )
    error_message = fields.Text(string="Error", readonly=True)

    _sql_constraints = [
        (
            "portal_shipping_notification_operation_user_uniq",
            "unique(operation_id, recipient_user_id)",
            "Ya existe un aviso automático para este usuario y operación.",
        ),
    ]
