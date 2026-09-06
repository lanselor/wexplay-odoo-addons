from odoo import _, api, models


class PortalDashboard(models.AbstractModel):
    _inherit = "wex.portal.dashboard"

    @api.model
    def _get_quick_actions(self, period):
        actions = super()._get_quick_actions(period)
        if self.env.user.has_group("stock.group_stock_user"):
            actions.append({
                "label": _("Facturación pendiente"), "description": _("Bandeja acumulada por empresa"),
                "icon": "fa fa-list-alt",
                "action": self.env["ir.actions.actions"]._for_xml_id(
                    "wexplay_portal_repair_billing.action_portal_billing_pending"),
            })
        return actions
