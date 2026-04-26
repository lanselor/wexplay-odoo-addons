from odoo import fields, models


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    type = fields.Selection(
        selection_add=[("wex_operational_list", "Operational List")],
        ondelete={"wex_operational_list": "cascade"},
    )

    def _get_view_info(self):
        view_info = super()._get_view_info()
        view_info["wex_operational_list"] = {"icon": "fa fa-table"}
        return view_info


class IrActionsActWindowView(models.Model):
    _inherit = "ir.actions.act_window.view"

    view_mode = fields.Selection(
        selection_add=[("wex_operational_list", "Operativa")],
        ondelete={"wex_operational_list": "cascade"},
    )
