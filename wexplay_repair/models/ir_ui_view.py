# -*- coding: utf-8 -*-

from odoo import fields, models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(
        selection_add=[
            ("repair_card", "Repair Cards"),
            ("repair_card_v2", "Repair Cards Compact"),
        ],
        ondelete={"repair_card": "cascade", "repair_card_v2": "cascade"},
    )

    def _is_qweb_based_view(self, view_type):
        return view_type in ("repair_card", "repair_card_v2") or super()._is_qweb_based_view(view_type)

    def _get_view_info(self):
        return {
            "repair_card": {"icon": "fa fa-window-maximize"},
            "repair_card_v2": {"icon": "fa fa-th-list"},
        } | super()._get_view_info()


class IrActionsActWindowView(models.Model):
    _inherit = "ir.actions.act_window.view"

    view_mode = fields.Selection(
        selection_add=[
            ("repair_card", "Repair Cards"),
            ("repair_card_v2", "Repair Cards Compact"),
        ],
        ondelete={"repair_card": "cascade", "repair_card_v2": "cascade"},
    )
