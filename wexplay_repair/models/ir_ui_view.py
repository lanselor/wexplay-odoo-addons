# -*- coding: utf-8 -*-

from odoo import fields, models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(
        selection_add=[("repair_card", "Repair Cards")],
        ondelete={"repair_card": "cascade"},
    )

    def _is_qweb_based_view(self, view_type):
        return view_type == "repair_card" or super()._is_qweb_based_view(view_type)

    def _get_view_info(self):
        return {"repair_card": {"icon": "fa fa-window-maximize"}} | super()._get_view_info()


class IrActionsActWindowView(models.Model):
    _inherit = "ir.actions.act_window.view"

    view_mode = fields.Selection(
        selection_add=[("repair_card", "Repair Cards")],
        ondelete={"repair_card": "cascade"},
    )
