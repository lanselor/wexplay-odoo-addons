# -*- coding: utf-8 -*-

from odoo.tests.common import SavepointCase


class TestWexplayRepairImages(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.storage = cls.env["dms.storage"].create(
            {
                "name": "Repair Images Test Storage",
                "save_type": "database",
            }
        )
        cls.company = cls.env.company
        cls.company.x_wex_consent_dms_storage_id = cls.storage
        cls.partner = cls.env["res.partner"].create({"name": "Cliente SAT"})
        cls.product = cls.env["product.product"].create({"name": "Equipo SAT"})
        cls.repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
            }
        )

    def test_upload_wizard_creates_image_and_sat_images_directory(self):
        tag = self.env["wex.image.tag"].search([("code", "=", "entrada")], limit=1)
        wizard = self.env["wex.repair.image.upload.wizard"].create(
            {
                "repair_order_id": self.repair.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "filename": "entrada-1.png",
                            "description": "Foto de entrada",
                            "tag_ids": [(6, 0, tag.ids)],
                            "image_file": "ZmFrZV9pbWFnZQ==",
                        },
                    )
                ],
            }
        )

        wizard.action_upload_images()

        image = self.env["wex.image.record"].search(
            [("repair_order_id", "=", self.repair.id)],
            limit=1,
        )
        self.assertTrue(image)
        self.assertEqual(image.dms_file_id.directory_id.name, "IMAGES")
        self.assertEqual(image.dms_file_id.directory_id.parent_id.name, self.repair.name)
        self.assertEqual(image.dms_file_id.directory_id.parent_id.parent_id.name, "SAT")
