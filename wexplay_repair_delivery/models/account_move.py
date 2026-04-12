# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def wex_get_sat_repairs(self):
        self.ensure_one()
        return self._get_sat_repairs()
