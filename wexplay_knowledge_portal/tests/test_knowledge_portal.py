from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestKnowledgePortal(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.article_model = cls.env["wex.knowledge.article"]

        cls.company_partner = cls.env["res.partner"].create({"name": "Portal Company"})
        cls.portal_contact = cls.env["res.partner"].create(
            {
                "name": "Portal Contact",
                "parent_id": cls.company_partner.id,
                "type": "contact",
            }
        )
        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Knowledge Portal User",
                "login": "knowledge.portal.user@example.com",
                "email": "knowledge.portal.user@example.com",
                "password": "knowledge_portal_test",
                "partner_id": cls.portal_contact.id,
                "groups_id": [(6, 0, [cls.portal_group.id])],
            }
        )
        cls.article = cls.article_model.create(
            {
                "name": "Portal Manual",
                "state": "published",
                "visibility": "internal",
                "portal_visible": True,
                "owner_id": cls.env.user.id,
            }
        )
        cls.private_portal_article = cls.article_model.create(
            {
                "name": "Specific Contact Manual",
                "state": "published",
                "visibility": "internal",
                "portal_contact_ids": [(6, 0, [cls.portal_contact.id])],
                "owner_id": cls.env.user.id,
            }
        )

    def test_portal_visible_article_is_readable_for_portal_user(self):
        self.assertTrue(self.article._can_user_read_portal_article(self.portal_user))

    def test_contact_list_article_is_readable_only_for_allowed_contact(self):
        self.assertTrue(self.private_portal_article._can_user_read_portal_article(self.portal_user))
        other_partner = self.env["res.partner"].create({"name": "Other Portal Contact"})
        other_user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Other Portal User",
                "login": "other.knowledge.portal.user@example.com",
                "email": "other.knowledge.portal.user@example.com",
                "password": "knowledge_portal_test_2",
                "partner_id": other_partner.id,
                "groups_id": [(6, 0, [self.portal_group.id])],
            }
        )
        self.assertFalse(self.private_portal_article._can_user_read_portal_article(other_user))

    def test_public_token_honours_expiry(self):
        article = self.article_model.create(
            {
                "name": "Public Manual",
                "state": "published",
                "visibility": "internal",
                "public_link_enabled": True,
                "public_access_expires_at": fields.Datetime.now() + timedelta(hours=1),
                "owner_id": self.env.user.id,
            }
        )
        self.assertTrue(article.public_access_token)
        self.assertTrue(article._can_read_public_article(article.public_access_token))
        article.public_access_expires_at = fields.Datetime.now() - timedelta(minutes=1)
        self.assertFalse(article._can_read_public_article(article.public_access_token))
