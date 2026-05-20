# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.tools import html2plaintext


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    x_wex_portal_repair_conversation_id = fields.Many2one(
        "wex.portal.repair.conversation",
        string="Conversación SAT portal",
        copy=False,
        index=True,
        ondelete="set null",
    )

    def _is_wex_portal_repair_operator_channel(self):
        self.ensure_one()
        return bool(getattr(self, "x_wex_portal_repair_conversation_id", False))

    def get_wex_portal_repair_sidebar_values(self):
        self.ensure_one()
        if not self._is_wex_portal_repair_operator_channel():
            return {"enabled": False}
        return self.x_wex_portal_repair_conversation_id.get_operator_chat_sidebar_values()

    def action_open_wex_portal_repair(self):
        self.ensure_one()
        if not self._is_wex_portal_repair_operator_channel():
            return False
        repair = self.x_wex_portal_repair_conversation_id.repair_id
        return {
            "type": "ir.actions.act_window",
            "name": repair.name,
            "res_model": "repair.order",
            "res_id": repair.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_wex_portal_customer(self):
        self.ensure_one()
        if not self._is_wex_portal_repair_operator_channel():
            return False
        partner = self.x_wex_portal_repair_conversation_id.repair_id.partner_id
        return {
            "type": "ir.actions.act_window",
            "name": partner.display_name,
            "res_model": "res.partner",
            "res_id": partner.id,
            "view_mode": "form",
            "target": "current",
        }

    def message_post(self, **kwargs):
        message = super().message_post(**kwargs)
        if (
            self.env.context.get("wex_portal_repair_skip_discuss_sync")
            or len(self) != 1
            or not self._is_wex_portal_repair_operator_channel()
        ):
            return message

        message_type = kwargs.get("message_type", "comment")
        if message_type != "comment":
            return message

        body_text = html2plaintext(kwargs.get("body") or message.body or "").strip()
        if not body_text:
            return message

        conversation = self.x_wex_portal_repair_conversation_id
        conversation.env["wex.portal.repair.message"].with_context(
            wex_portal_repair_skip_operator_channel_projection=True,
        ).create(
            {
                "conversation_id": conversation.id,
                "body": body_text,
                "source": "technician",
                "visible_to_customer": True,
                "author_user_id": self.env.user.id,
                "author_partner_id": self.env.user.partner_id.id,
                "author_name": self.env.user.display_name,
            }
        )
        return message
