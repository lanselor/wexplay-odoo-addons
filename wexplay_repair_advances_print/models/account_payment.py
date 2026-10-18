from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_qz_print_advance_receipt(self):
        self.action_print_advance_receipt()
        return {
            "type": "ir.actions.client", "tag": "wexplay_sat_print.print_report_qz",
            "params": {
                "kind": "thermal", "document_code": "sat_advance_receipt",
                "report_name": "wexplay_repair_advances.advance_receipt", "res_id": self.id,
            },
        }
