# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestPortalRepairSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.company_partner = cls.env["res.partner"].create({"name": "Empresa Portal"})
        cls.contact_partner = cls.env["res.partner"].create(
            {
                "name": "Contacto Portal",
                "parent_id": cls.company_partner.id,
                "type": "contact",
            }
        )
        cls.other_partner = cls.env["res.partner"].create({"name": "Otra Empresa"})
        cls.product = cls.env["product.product"].create({"name": "Equipo Portal"})
        cls.service_product = cls.env["product.product"].create(
            {
                "name": "Servicio Portal",
                "type": "service",
                "list_price": 42.0,
            }
        )

        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Portal User",
                "login": "portal.user.wexplay@example.com",
                "email": "portal.user.wexplay@example.com",
                "partner_id": cls.contact_partner.id,
                "groups_id": [(6, 0, [cls.portal_group.id])],
            }
        )

        cls.own_repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.company_partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_reported_issue": "No enciende",
            }
        )
        cls.contact_repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.contact_partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_reported_issue": "Pantalla rota",
            }
        )
        cls.foreign_repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.other_partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_reported_issue": "Bateria agotada",
            }
        )
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.company_partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.service_product.id,
                            "name": "Mano de obra portal",
                            "product_uom_qty": 1.0,
                            "product_uom": cls.service_product.uom_id.id,
                            "price_unit": 42.0,
                        },
                    )
                ],
            }
        )
        cls.own_repair.sale_order_id = cls.sale_order

    def test_portal_visible_domain_uses_commercial_partner(self):
        domain = self.env["repair.order"]._get_portal_visible_domain(self.portal_user)
        repairs = self.env["repair.order"].search(domain)

        self.assertIn(self.own_repair, repairs)
        self.assertIn(self.contact_repair, repairs)
        self.assertNotIn(self.foreign_repair, repairs)

    def test_portal_user_only_reads_company_repairs(self):
        portal_repairs = self.env["repair.order"].with_user(self.portal_user).search([])

        self.assertIn(self.own_repair, portal_repairs)
        self.assertIn(self.contact_repair, portal_repairs)
        self.assertNotIn(self.foreign_repair, portal_repairs)

    def test_can_portal_user_access_matches_same_rule(self):
        self.assertTrue(self.own_repair._can_portal_user_access(self.portal_user))
        self.assertTrue(self.contact_repair._can_portal_user_access(self.portal_user))
        self.assertFalse(self.foreign_repair._can_portal_user_access(self.portal_user))

    def test_portal_related_helpers_do_not_bypass_access_with_sudo(self):
        foreign_repair = self.foreign_repair.with_user(self.portal_user)

        with self.assertRaises(AccessError):
            foreign_repair._get_portal_part_line_values()

        with self.assertRaises(AccessError):
            foreign_repair._get_portal_service_line_values()

        with self.assertRaises(AccessError):
            foreign_repair._get_portal_brand_label()

        with self.assertRaises(AccessError):
            foreign_repair._get_portal_image_values()

        with self.assertRaises(AccessError):
            foreign_repair._get_portal_invoice_values()

    def test_portal_user_can_read_prepared_service_lines_from_own_repair(self):
        values = self.own_repair.with_user(self.portal_user)._get_portal_service_line_values()

        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]["name"], self.service_product.display_name)

    def test_portal_shows_warranty_for_an_open_repair_without_coverage(self):
        if "x_warranty_status" not in self.own_repair._fields:
            self.skipTest("El módulo de garantías no está instalado.")

        values = self.own_repair.with_user(
            self.portal_user
        )._get_portal_warranty_values()

        self.assertTrue(values["show"])
        self.assertFalse(values["is_valid"])

    def _set_reception_inspection(self):
        self.own_repair.write({
            "x_device_type": "mobile", "x_device_description": "Portal device description",
            "x_device_condition_ids": [Command.set(self.env.ref("wexplay_repair.device_condition_broken_screen").ids)],
            "x_device_inspection_marks": {"device_type": "mobile", "front": [[[0.1, 0.2]]], "back": []},
        })
        return self.own_repair.with_user(self.portal_user)

    def _signed_reception(self, snapshot):
        if "wex.consent.document" not in self.env:
            self.skipTest("Optional consent module is not installed")
        import json
        return self.env["wex.consent.document"].create({
            "name": "Portal signed snapshot", "repair_order_id": self.own_repair.id,
            "document_type": "reception", "snapshot_json": json.dumps(snapshot), "state": "signed",
        })

    def test_portal_inspection_requires_own_repair(self):
        self._set_reception_inspection()
        with self.assertRaises(AccessError):
            self.foreign_repair.with_user(self.portal_user)._get_portal_reception_inspection_values()
        with self.assertRaises(AccessError):
            self.foreign_repair.with_user(self.portal_user).sudo()._get_portal_reception_inspection_values()
        with self.assertRaises(AccessError):
            self.own_repair.with_user(self.env.ref("base.public_user"))._get_portal_reception_inspection_values()

    def test_portal_inspection_values_are_allowlisted(self):
        repair = self._set_reception_inspection()
        self.own_repair.x_internal_notes = "PRIVATE TECHNICIAN NOTES"
        values = repair._get_portal_reception_inspection_values()
        self.assertEqual(set(values), {"description", "conditions", "views", "source_label"})
        self.assertEqual(values["description"], "Portal device description")
        self.assertEqual(len(values["views"]), 2)
        self.assertNotIn("PRIVATE TECHNICIAN NOTES", str(values))
        self.assertTrue(all(set(view) == {"label", "src"} for view in values["views"]))
        with self.assertRaises(AccessError):
            repair.read(["x_device_inspection_marks", "x_device_condition_ids"])
        with self.assertRaises(AccessError), self.cr.savepoint():
            repair.write({"x_device_description": "Portal write"})

    def test_empty_portal_inspection_is_omitted(self):
        self.assertFalse(self.own_repair.with_user(self.portal_user)._get_portal_reception_inspection_values())
        self.own_repair.write({"x_device_type": "console", "x_device_inspection_marks": {
            "device_type": "console", "console_format": "desktop", "front": [], "back": [],
        }})
        self.assertFalse(self.own_repair.with_user(self.portal_user)._get_portal_reception_inspection_values())

    def test_portal_signed_snapshot_has_priority_and_no_model_access(self):
        repair = self._set_reception_inspection()
        original = self.own_repair._prepare_device_inspection_snapshot()
        original["secret"] = "DO NOT EXPOSE"
        document = self._signed_reception({"device_inspection": original, "legal_text": "PRIVATE LEGAL SNAPSHOT"})
        self.own_repair.write({"x_device_description": "Edited after signing", "x_device_inspection_marks": False})
        with patch.object(type(self.own_repair), "_prepare_device_inspection_snapshot", side_effect=AssertionError("live repair read")):
            values = repair._get_portal_reception_inspection_values()
        self.assertEqual(values["description"], "Portal device description")
        self.assertEqual(len(values["views"]), 2)
        self.assertNotIn("DO NOT EXPOSE", str(values))
        self.assertNotIn("PRIVATE LEGAL SNAPSHOT", str(values))
        with self.assertRaises(AccessError):
            document.with_user(self.portal_user).read(["snapshot_json"])

    def test_portal_legacy_signed_reception_does_not_merge_live_marks(self):
        repair = self._set_reception_inspection()
        self._signed_reception({"device_description": "Legacy signed description"})
        values = repair._get_portal_reception_inspection_values()
        self.assertEqual(values["description"], "Legacy signed description")
        self.assertFalse(values["conditions"])
        self.assertFalse(values["views"])

    def test_portal_empty_signed_reception_does_not_fall_back(self):
        repair = self._set_reception_inspection()
        self._signed_reception({"device_inspection": False})
        self.assertFalse(repair._get_portal_reception_inspection_values())

    def test_pending_reception_uses_current_registered_inspection(self):
        repair = self._set_reception_inspection()
        if "wex.consent.document" not in self.env:
            self.skipTest("Optional consent module is not installed")
        self.env["wex.consent.document"].create({
            "name": "Pending portal snapshot", "repair_order_id": self.own_repair.id,
            "document_type": "reception", "state": "pending_signature",
            "snapshot_json": '{"device_inspection":{"description":"PENDING SECRET"}}',
        })
        self.assertEqual(repair._get_portal_reception_inspection_values()["description"], "Portal device description")

    def test_portal_inspection_rejects_remote_image_urls(self):
        values = self.env["repair.order"]._prepare_portal_inspection_values({
            "description": "Registered text", "conditions": [],
            "views": [{"label": "External", "src": "https://example.invalid/tracking.svg"}],
        })
        self.assertFalse(values["views"])
