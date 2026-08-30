# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo.tests.common import SavepointCase


class TestPortalShippingNotifications(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.internal_group = cls.env.ref("base.group_user")
        cls.company_partner = cls.env["res.partner"].create(
            {"name": "Empresa Avisos Portal"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Equipo Avisos Portal"}
        )
        cls.portal_user = cls._create_user(
            "portal.shipping.one@example.com",
            cls.portal_group,
        )
        cls.second_portal_user = cls._create_user(
            "portal.shipping.two@example.com",
            cls.portal_group,
        )
        cls.internal_user = cls._create_user(
            "internal.shipping@example.com",
            cls.internal_group,
        )
        cls.repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.company_partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_requires_shipping": True,
            }
        )
        cls.operation = cls.env["wex.repair.shipping.operation"].create(
            {"repair_id": cls.repair.id, "operation_type": "pickup"}
        )

    @classmethod
    def _create_user(cls, login, group):
        partner = cls.env["res.partner"].create(
            {"name": login, "email": login, "parent_id": cls.company_partner.id}
        )
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": login,
                "login": login,
                "email": login,
                "partner_id": partner.id,
                "groups_id": [(6, 0, [group.id])],
            }
        )

    def test_only_active_portal_users_receive_one_notification_per_operation(self):
        template = self.env.ref(
            "wexplay_portal_repair_delivery.mail_template_portal_repair_shipping_ready"
        )

        with patch.object(type(template), "send_mail", return_value=False) as send_mail:
            self.operation._queue_portal_shipping_notifications(template)
            self.operation._queue_portal_shipping_notifications(template)

        notifications = self.env["wex.portal.repair.shipping.notification"].search(
            [("operation_id", "=", self.operation.id)]
        )
        self.assertEqual(len(notifications), 2)
        self.assertSetEqual(
            set(notifications.mapped("recipient_user_id").ids),
            {self.portal_user.id, self.second_portal_user.id},
        )
        self.assertNotIn(self.internal_user.id, notifications.mapped("recipient_user_id").ids)
        self.assertEqual(send_mail.call_count, 2)
