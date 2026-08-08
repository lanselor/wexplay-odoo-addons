# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestWexPrintDeviceSetupWizard(TransactionCase):
    def setUp(self):
        super().setUp()
        self.snapshot = self.env["wex.print.device.snapshot"].create({
            "name": "Brother QL-820NWB",
            "printer_name": "Brother QL-820NWB",
            "driver": "Brother QL-820NWB",
        })
        self.document_type = self.env.ref("wex_print_core.wex_print_document_type_sat_label_main")

    def test_setup_wizard_creates_device_profile_and_assignment(self):
        wizard = self.env["wex.print.device.setup.wizard"].with_context(
            default_snapshot_id=self.snapshot.id,
        ).create({
            "document_line_ids": [(0, 0, {"document_type_id": self.document_type.id})],
        })

        wizard.action_apply()

        device = self.env["wex.print.device"].search(
            [("qz_printer_name", "=", self.snapshot.printer_name)],
            limit=1,
        )
        self.assertTrue(device)
        self.assertEqual(device.device_kind, "label")

        profile = self.env["wex.print.profile"].search(
            [("device_id", "=", device.id)],
            limit=1,
        )
        self.assertTrue(profile)
        self.assertFalse(profile.printer_name)

        assignment = self.env["wex.print.assignment"].search([
            ("document_type_id", "=", self.document_type.id),
            ("profile_id", "=", profile.id),
            ("user_id", "=", self.env.user.id),
        ], limit=1)
        self.assertTrue(assignment)
        self.assertFalse(assignment.pilot_use_new_resolution)

    def test_snapshot_opens_setup_wizard_for_new_device(self):
        action = self.snapshot.action_open_setup_wizard()

        self.assertEqual(action["res_model"], "wex.print.device.setup.wizard")
        self.assertEqual(action["target"], "new")

    def test_existing_device_wizard_adds_a_document_without_duplicate_device(self):
        initial_wizard = self.env["wex.print.device.setup.wizard"].with_context(
            default_snapshot_id=self.snapshot.id,
        ).create({
            "document_line_ids": [(0, 0, {"document_type_id": self.document_type.id})],
        })
        initial_wizard.action_apply()
        device = self.env["wex.print.device"].search(
            [("qz_printer_name", "=", self.snapshot.printer_name)],
            limit=1,
        )
        accessory_document = self.env.ref(
            "wex_print_core.wex_print_document_type_sat_label_accessory"
        )

        action = device.action_open_document_setup_wizard()
        self.assertEqual(action["context"]["default_existing_device_id"], device.id)

        wizard = self.env["wex.print.device.setup.wizard"].with_context(
            default_existing_device_id=device.id,
        ).create({
            "document_line_ids": [(0, 0, {"document_type_id": accessory_document.id})],
        })
        wizard.action_apply()

        devices = self.env["wex.print.device"].search(
            [("qz_printer_name", "=", self.snapshot.printer_name)]
        )
        self.assertEqual(len(devices), 1)
        device.invalidate_recordset(["assignment_ids"])
        self.assertEqual(
            set(device.assignment_ids.mapped("document_type_id").ids),
            {self.document_type.id, accessory_document.id},
        )
