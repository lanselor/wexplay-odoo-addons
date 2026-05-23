# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase


class TestPortalRepairCommunication(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.company_partner = cls.env["res.partner"].create({"name": "Empresa SAT Chat"})
        cls.contact_partner = cls.env["res.partner"].create(
            {
                "name": "Contacto SAT Chat",
                "parent_id": cls.company_partner.id,
                "type": "contact",
            }
        )
        cls.product = cls.env["product.product"].create({"name": "Equipo SAT Chat"})
        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Portal SAT User",
                "login": "portal.sat.chat@example.com",
                "email": "portal.sat.chat@example.com",
                "partner_id": cls.contact_partner.id,
                "groups_id": [(6, 0, [cls.portal_group.id])],
            }
        )
        cls.responsible_a = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Tecnico A",
                "login": "tecnico.a.portal.chat@example.com",
                "email": "tecnico.a.portal.chat@example.com",
            }
        )
        cls.responsible_b = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Tecnico B",
                "login": "tecnico.b.portal.chat@example.com",
                "email": "tecnico.b.portal.chat@example.com",
            }
        )
        cls.repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.company_partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_reported_issue": "No arranca",
                "user_id": cls.responsible_a.id,
            }
        )

    def test_get_or_create_portal_conversation_is_unique_per_repair(self):
        conversation_1 = self.repair._get_or_create_portal_conversation()
        conversation_2 = self.repair._get_or_create_portal_conversation()

        self.assertEqual(conversation_1, conversation_2)
        self.assertEqual(
            self.env["wex.portal.repair.conversation"].search_count(
                [("repair_id", "=", self.repair.id)]
            ),
            1,
        )

    def test_customer_write_depends_on_active_sat_or_valid_warranty(self):
        repair_model = type(self.repair)
        with patch.object(repair_model, "_is_portal_repair_active", lambda self: True, create=True):
            self.assertTrue(self.repair._can_portal_customer_write_conversation())

        with patch.object(repair_model, "_is_portal_repair_active", lambda self: False, create=True):
            expected = bool(
                "x_is_any_warranty_valid" in self.repair._fields
                and self.repair.x_is_any_warranty_valid
            )
            self.assertEqual(
                self.repair._can_portal_customer_write_conversation(),
                expected,
            )

    def test_reassigning_responsible_keeps_same_conversation_and_archives_old_member(self):
        conversation = self.repair._get_or_create_portal_conversation()
        channel = conversation._get_or_create_operator_channel()
        old_member = channel.channel_member_ids.filtered(
            lambda member: member.partner_id == self.responsible_a.partner_id
        )

        self.assertTrue(old_member)
        self.repair.write({"user_id": self.responsible_b.id})
        conversation.invalidate_recordset(["responsible_user_id"])
        channel.invalidate_recordset(["channel_member_ids"])

        self.assertEqual(conversation.responsible_user_id, self.responsible_b)

        archived_old_member = channel.channel_member_ids.filtered(
            lambda member: member.partner_id == self.responsible_a.partner_id
        )
        new_member = channel.channel_member_ids.filtered(
            lambda member: member.partner_id == self.responsible_b.partner_id
        )

        self.assertTrue(archived_old_member)
        self.assertTrue(new_member)
        self.assertEqual(archived_old_member.fold_state, "closed")
        self.assertEqual(archived_old_member.custom_notifications, "no_notif")
        self.assertEqual(new_member.fold_state, "open")

    def test_technician_message_post_syncs_back_to_functional_conversation(self):
        conversation = self.repair._get_or_create_portal_conversation()
        channel = conversation._get_or_create_operator_channel()

        channel.with_user(self.responsible_a).message_post(
            body="<p>Respuesta tecnico</p>",
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
        )

        technician_messages = conversation.message_ids.filtered(
            lambda message: message.source == "technician"
            and message.body == "Respuesta tecnico"
        )
        self.assertEqual(len(technician_messages), 1)

    def test_customer_view_excludes_internal_system_messages(self):
        conversation = self.repair._get_or_create_portal_conversation()
        self.env["wex.portal.repair.message"].create(
            {
                "conversation_id": conversation.id,
                "body": "Nota interna",
                "source": "system",
                "visible_to_customer": False,
            }
        )

        customer_messages = self.repair._get_portal_conversation_message_values(
            customer_view=True
        )
        self.assertFalse(
            any(
                item.get("type") == "message" and item.get("body") == "Nota interna"
                for item in customer_messages
            )
        )

    def test_pending_operator_chat_event_payload_returns_unread_conversation(self):
        conversation = self.repair._get_or_create_portal_conversation()
        self.env["wex.portal.repair.message"].sudo().create(
            {
                "conversation_id": conversation.id,
                "body": "Cliente pendiente",
                "source": "portal_customer",
                "visible_to_customer": True,
                "author_user_id": self.portal_user.id,
                "author_partner_id": self.company_partner.id,
                "author_name": self.company_partner.display_name,
            }
        )

        payload = (
            self.env["wex.portal.repair.conversation"]
            .with_user(self.responsible_a)
            .get_pending_operator_chat_event_payload()
        )

        self.assertTrue(payload)
        self.assertEqual(payload["conversation_id"], conversation.id)
        self.assertEqual(payload["repair_id"], self.repair.id)
        self.assertTrue(payload["channel_id"])

        conversation.sudo().write(
            {"technician_last_read_at": fields.Datetime.now()}
        )
        payload_after_read = (
            self.env["wex.portal.repair.conversation"]
            .with_user(self.responsible_a)
            .get_pending_operator_chat_event_payload()
        )
        self.assertFalse(payload_after_read)
