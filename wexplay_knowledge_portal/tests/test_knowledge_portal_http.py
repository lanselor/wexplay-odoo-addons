from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestKnowledgePortalHTTP(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.company_partner = cls.env["res.partner"].create({"name": "Portal HTTP Company"})
        cls.portal_contact = cls.env["res.partner"].create(
            {
                "name": "Portal HTTP Contact",
                "parent_id": cls.company_partner.id,
                "type": "contact",
            }
        )
        cls.portal_password = "knowledge_http_123"
        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Knowledge HTTP User",
                "login": "knowledge.http.user@example.com",
                "email": "knowledge.http.user@example.com",
                "password": cls.portal_password,
                "partner_id": cls.portal_contact.id,
                "groups_id": [(6, 0, [cls.portal_group.id])],
            }
        )
        cls.portal_article = cls.env["wex.knowledge.article"].create(
            {
                "name": "HTTP Portal Knowledge",
                "state": "published",
                "visibility": "internal",
                "portal_visible": True,
                "owner_id": cls.env.user.id,
            }
        )
        cls.public_article = cls.env["wex.knowledge.article"].create(
            {
                "name": "HTTP Public Knowledge",
                "state": "published",
                "visibility": "internal",
                "public_link_enabled": True,
                "owner_id": cls.env.user.id,
            }
        )

    def test_portal_user_can_open_knowledge_detail(self):
        self.authenticate(self.portal_user.login, self.portal_password)
        response = self.url_open("/my/knowledge/%s" % self.portal_article.id)
        self.assertEqual(response.status_code, 200)

    def test_public_token_route_is_available(self):
        response = self.url_open("/knowledge/public/%s" % self.public_article.public_access_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Robots-Tag"), "noindex, nofollow")
