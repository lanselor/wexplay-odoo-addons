# -*- coding: utf-8 -*-

from odoo import models


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    def _get_default_pdf_report_id(self, move):
        if move._should_use_sat_invoice_report():
            return move._get_sat_invoice_report()
        return super()._get_default_pdf_report_id(move)
