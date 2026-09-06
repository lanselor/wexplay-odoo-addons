from odoo.tests.common import TransactionCase


class TestPartnerPortalStatus(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.partner"].create({"name": "Portal company", "is_company": True})
        cls.other_company = cls.env["res.partner"].create({"name": "Other company", "is_company": True})
        cls.contact = cls.env["res.partner"].create({"name": "Portal contact", "parent_id": cls.company.id})
        cls.colleague = cls.env["res.partner"].create({"name": "Without access", "parent_id": cls.company.id})
        cls.user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Portal contact", "login": "wex.portal.status@example.com",
            "partner_id": cls.contact.id,
            "groups_id": [(6, 0, [cls.env.ref("base.group_portal").id])],
        })

    def _assert_portal_status(self, active_partners):
        partners = self.company | self.other_company | self.contact | self.colleague
        partners.invalidate_recordset(["wex_has_active_portal"])
        self.assertEqual(set(partners.filtered("wex_has_active_portal").ids), set(active_partners.ids))
        for operator, value, expected in (
            ("=", True, active_partners), ("!=", False, active_partners),
            ("=", False, partners - active_partners), ("!=", True, partners - active_partners),
        ):
            found = self.env["res.partner"].search([
                ("id", "in", partners.ids), ("wex_has_active_portal", operator, value),
            ])
            self.assertEqual(set(found.ids), set(expected.ids))

    def test_company_status_does_not_grant_colleague_access(self):
        self._assert_portal_status(self.company | self.contact)

    def test_archived_and_reactivated_user(self):
        self.user.active = False
        self._assert_portal_status(self.env["res.partner"])
        self.user.active = True
        self._assert_portal_status(self.company | self.contact)

    def test_revoked_portal_and_internal_user(self):
        self.user.groups_id = [(6, 0, [self.env.ref("base.group_user").id])]
        self._assert_portal_status(self.env["res.partner"])

    def test_contact_changes_company(self):
        self.contact.parent_id = self.other_company
        self._assert_portal_status(self.other_company | self.contact)

    def test_company_has_own_portal_user(self):
        self.user.partner_id = self.company
        self._assert_portal_status(self.company)

    def test_nested_contact_uses_commercial_company(self):
        self.contact.parent_id = self.colleague
        self._assert_portal_status(self.company | self.contact)

    def test_internal_reader_without_user_administration(self):
        reader = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Contact reader", "login": "wex.portal.reader@example.com",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        self.assertTrue(self.company.with_user(reader).wex_has_active_portal)
        found = self.env["res.partner"].with_user(reader).search([
            ("id", "=", self.company.id), ("wex_has_active_portal", "=", True),
        ])
        self.assertEqual(found.id, self.company.id)

    def test_indicator_is_not_exposed_to_portal_users(self):
        self.assertNotIn(
            "wex_has_active_portal",
            self.env["res.partner"].with_user(self.user).fields_get(),
        )
