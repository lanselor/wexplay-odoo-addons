from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    vendor_bill_ocr_job_count = fields.Integer(
        compute="_compute_vendor_bill_ocr_job_count",
        string="OCR Jobs",
    )

    def _compute_vendor_bill_ocr_job_count(self):
        grouped = self.env["wex.vendor.bill.ocr.job"].read_group(
            [("purchase_order_id", "in", self.ids)],
            ["purchase_order_id"],
            ["purchase_order_id"],
        )
        counts = {
            item["purchase_order_id"][0]: item["purchase_order_id_count"]
            for item in grouped
        }
        for order in self:
            order.vendor_bill_ocr_job_count = counts.get(order.id, 0)

    def action_open_vendor_bill_ocr_upload(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Upload Vendor Bill PDF",
            "res_model": "wex.vendor.bill.ocr.upload.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_purchase_order_id": self.id,
            },
        }

    def action_view_vendor_bill_ocr_jobs(self):
        self.ensure_one()
        action = self.env.ref(
            "wex_vendor_bill_ocr.action_wex_vendor_bill_ocr_job"
        ).read()[0]
        action["domain"] = [("purchase_order_id", "=", self.id)]
        action["context"] = {
            "default_purchase_order_id": self.id,
        }
        if self.vendor_bill_ocr_job_count == 1:
            action["view_mode"] = "form"
            action["res_id"] = self.env["wex.vendor.bill.ocr.job"].search(
                [("purchase_order_id", "=", self.id)],
                limit=1,
            ).id
        return action
