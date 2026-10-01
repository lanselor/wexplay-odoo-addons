# -*- coding: utf-8 -*-
from odoo import _, models
from odoo.exceptions import UserError


class WexTeardownBatchPrint(models.Model):
    _inherit = "wex.teardown.batch"

    def action_get_zebra_batch_label_payload(self):
        self.ensure_one()
        self.check_access("read")
        if not self.name or self.name == "/":
            raise UserError(_("Guarde el despiece antes de imprimir su etiqueta."))
        return {
            "document_code": "teardown_batch_label_zebra",
            "report_name": "wex_teardown.report_teardown_batch_label_zebra_76x25",
            "reference": self.name,
        }