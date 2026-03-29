from odoo.exceptions import ValidationError
from odoo.tests.common import SavepointCase


class TestWexItMaintenance(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "ACME Systems",
            "x_is_it_maintenance_customer": True,
        })
        cls.template = cls.env["wex.it.maintenance.template"].create({
            "name": "Monthly Preventive",
            "line_ids": [
                (0, 0, {"sequence": 10, "name": "Check system updates"}),
                (0, 0, {"sequence": 20, "name": "Check antivirus"}),
            ],
        })

    def test_asset_internal_code_generation(self):
        asset_1 = self.env["wex.it.asset"].create({
            "name": "Reception Laptop",
            "partner_id": self.partner.id,
            "asset_type": "laptop",
        })
        asset_2 = self.env["wex.it.asset"].create({
            "name": "Manager Laptop",
            "partner_id": self.partner.id,
            "asset_type": "laptop",
        })

        self.assertEqual(asset_1.internal_code, "ACME-PORT-001")
        self.assertEqual(asset_2.internal_code, "ACME-PORT-002")
        self.assertEqual(
            self.env["wex.it.asset"]._get_next_internal_code_number(self.partner.id, "laptop", asset_1.company_id.id),
            3,
        )

    def test_partner_contract_dates_validation(self):
        with self.assertRaises(ValidationError):
            self.partner.write({
                "contract_start_date": "2026-03-10",
                "contract_end_date": "2026-03-01",
            })

    def test_visit_template_and_asset_review_creation(self):
        asset = self.env["wex.it.asset"].create({
            "name": "Main Server",
            "partner_id": self.partner.id,
            "asset_type": "server",
        })
        visit = self.env["wex.it.maintenance.visit"].create({
            "partner_id": self.partner.id,
            "template_id": self.template.id,
            "line_ids": [
                (0, 0, {
                    "asset_id": asset.id,
                    "action_performed": "Checked storage and updates",
                    "result": "attention",
                    "issue_found": "Low free disk space",
                    "observations": "Plan storage cleanup",
                }),
            ],
        })

        self.assertEqual(len(visit.checklist_line_ids), 2)
        visit.action_done()

        self.assertEqual(visit.state, "done")
        self.assertEqual(len(visit.review_ids), 1)
        self.assertEqual(visit.review_ids.health_status, "attention")

    def test_models_inherit_company_from_partner(self):
        company = self.env["res.company"].create({"name": "ACME Managed"})
        partner = self.env["res.partner"].create({
            "name": "Managed Customer",
            "x_is_it_maintenance_customer": True,
            "company_id": company.id,
        })

        asset = self.env["wex.it.asset"].create({
            "name": "Firewall",
            "partner_id": partner.id,
            "asset_type": "router",
        })
        service = self.env["wex.it.service"].create({
            "name": "VPN",
            "partner_id": partner.id,
            "service_type": "vpn",
        })
        visit = self.env["wex.it.maintenance.visit"].create({
            "partner_id": partner.id,
        })

        self.assertEqual(asset.company_id, company)
        self.assertEqual(service.company_id, company)
        self.assertEqual(visit.company_id, company)

    def test_credential_inherits_customer_from_asset(self):
        asset = self.env["wex.it.asset"].create({
            "name": "VPN Appliance",
            "partner_id": self.partner.id,
            "asset_type": "router",
        })

        credential = self.env["wex.it.credential"].create({
            "name": "VPN Admin",
            "asset_id": asset.id,
            "credential_type": "password",
            "secret_value": "secret",
        })

        self.assertEqual(credential.partner_id, self.partner)
        self.assertEqual(credential.company_id, asset.company_id)
