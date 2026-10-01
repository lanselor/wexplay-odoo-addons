from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductZebraLabel(TransactionCase):
    def test_zebra_label_payload_uses_internal_reference(self):
        product = self.env["product.template"].create({
            "name": "Zebra product label test",
            "default_code": "WP-OD-0001",
            "list_price": 24.95,
        })
        payload = product.action_get_zebra_label_payload()
        self.assertEqual(payload["document_code"], "product_label_zebra")
        self.assertEqual(payload["reference"], "WP-OD-0001")
        self.assertEqual(
            payload["report_name"],
            "wexplay_product_print.report_product_label_zebra_76x25",
        )