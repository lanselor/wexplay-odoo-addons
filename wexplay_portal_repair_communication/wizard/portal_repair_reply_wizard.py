# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import UserError


class WexPortalRepairReplyWizard(models.TransientModel):
    _name = "wex.portal.repair.reply.wizard"
    _description = "Reply to SAT portal conversation"

    conversation_id = fields.Many2one(
        "wex.portal.repair.conversation",
        string="Conversación",
        required=True,
        readonly=True,
    )
    mark_no_response_needed = fields.Boolean(
        string="No es necesaria contestación",
        default=False,
    )
    body = fields.Text(
        string="Respuesta",
    )

    def action_send(self):
        self.ensure_one()
        conversation = self.conversation_id
        if self.mark_no_response_needed and not (self.body or "").strip():
            conversation.action_mark_no_response_needed()
            return {"type": "ir.actions.act_window_close"}

        body = (self.body or "").strip()
        if not body:
            raise UserError(_("Debes escribir una respuesta o marcar que no es necesaria."))

        self.env["wex.portal.repair.message"].create(
            {
                "conversation_id": conversation.id,
                "body": body,
                "source": "technician",
                "visible_to_customer": True,
            }
        )
        return {"type": "ir.actions.act_window_close"}
