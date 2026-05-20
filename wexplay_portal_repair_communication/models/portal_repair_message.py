# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WexPortalRepairMessage(models.Model):
    _name = "wex.portal.repair.message"
    _description = "SAT portal conversation message"
    _order = "create_date asc, id asc"

    conversation_id = fields.Many2one(
        "wex.portal.repair.conversation",
        string="Conversation",
        required=True,
        ondelete="cascade",
        index=True,
    )
    repair_id = fields.Many2one(
        related="conversation_id.repair_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="conversation_id.company_id",
        store=True,
        readonly=True,
    )
    author_user_id = fields.Many2one(
        "res.users",
        string="Usuario autor",
        readonly=True,
    )
    author_partner_id = fields.Many2one(
        "res.partner",
        string="Partner autor",
        readonly=True,
    )
    author_name = fields.Char(string="Autor", readonly=True)
    source = fields.Selection(
        [
            ("portal_customer", "Cliente portal"),
            ("technician", "Técnico"),
            ("system", "Sistema"),
        ],
        string="Origen",
        required=True,
        default="technician",
        index=True,
    )
    visible_to_customer = fields.Boolean(
        string="Visible cliente",
        default=True,
    )
    body = fields.Text(
        string="Mensaje",
        required=True,
    )
    is_customer_message = fields.Boolean(
        string="Mensaje cliente",
        compute="_compute_flags",
    )
    is_technician_message = fields.Boolean(
        string="Mensaje técnico",
        compute="_compute_flags",
    )

    @api.depends("source")
    def _compute_flags(self):
        for message in self:
            message.is_customer_message = message.source == "portal_customer"
            message.is_technician_message = message.source == "technician"

    @api.constrains("body")
    def _check_body(self):
        for message in self:
            if not (message.body or "").strip():
                raise ValidationError(_("El mensaje no puede estar vacío."))

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(self._prepare_create_vals_list(vals_list))
        messages._apply_conversation_side_effects()
        return messages

    def _prepare_create_vals_list(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            prepared_vals = dict(vals)
            prepared_vals["body"] = (prepared_vals.get("body") or "").strip()
            source = prepared_vals.get("source") or "technician"
            prepared_vals["source"] = source
            if not prepared_vals.get("author_user_id") and self.env.user:
                prepared_vals["author_user_id"] = self.env.user.id
            if not prepared_vals.get("author_partner_id") and self.env.user.partner_id:
                prepared_vals["author_partner_id"] = self.env.user.partner_id.id
            if not prepared_vals.get("author_name"):
                prepared_vals["author_name"] = (
                    self.env.user.display_name
                    if source != "portal_customer"
                    else self.env.user.partner_id.display_name
                )
            if source == "system":
                prepared_vals["visible_to_customer"] = False
            prepared_vals_list.append(prepared_vals)
        return prepared_vals_list

    def _apply_conversation_side_effects(self):
        for message in self:
            conversation = message.conversation_id
            update_vals = {
                "last_message_at": message.create_date,
                "last_message_preview": message.body[:160],
            }
            if message.source == "portal_customer":
                update_vals.update(
                    {
                        "state": "pending_customer_reply",
                        "last_customer_message_at": message.create_date,
                        "no_response_needed_at": False,
                        "no_response_needed_by_id": False,
                    }
                )
                conversation.write(update_vals)
                conversation.repair_id._notify_responsible_about_portal_message(message)
            elif message.source == "technician":
                update_vals.update(
                    {
                        "state": "answered",
                        "last_technician_message_at": message.create_date,
                        "no_response_needed_at": False,
                        "no_response_needed_by_id": False,
                    }
                )
                conversation.write(update_vals)
            else:
                conversation.write(update_vals)

            if not self.env.context.get("wex_portal_repair_skip_operator_channel_projection"):
                conversation._post_message_to_operator_channel(message)
