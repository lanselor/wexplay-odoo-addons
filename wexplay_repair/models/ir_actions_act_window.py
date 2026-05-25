# -*- coding: utf-8 -*-

from odoo import api, models


class IrActionsActWindow(models.Model):
    _inherit = "ir.actions.act_window"

    @api.model
    def _wexplay_configure_repair_order_tree_views(self):
        action = self.env.ref("repair.action_repair_order_tree", raise_if_not_found=False)
        repair_card_view = self.env.ref("wexplay_repair.view_repair_order_card", raise_if_not_found=False)
        if not action or not repair_card_view:
            return

        repair_card_v2_view = self.env.ref("wexplay_repair.view_repair_order_card_v2", raise_if_not_found=False)

        action.write({
            "view_id": repair_card_view.id,
            "view_mode": "repair_card,repair_card_v2,list,kanban,graph,pivot,form,activity",
            "context": "{'search_default_group_by_create_date_day': 1, 'search_default_wex_my_repairs': 1}",
        })

        action_view_model = self.env["ir.actions.act_window.view"].sudo()
        repair_card_action_view = action.view_ids.filtered(lambda view: view.view_mode == "repair_card")[:1]
        if not repair_card_action_view:
            repair_card_action_view = action_view_model.create({
                "act_window_id": action.id,
                "view_id": repair_card_view.id,
                "view_mode": "repair_card",
                "sequence": 1,
            })

        if repair_card_v2_view:
            repair_card_v2_action_view = action.view_ids.filtered(lambda view: view.view_mode == "repair_card_v2")[:1]
            if not repair_card_v2_action_view:
                action_view_model.create({
                    "act_window_id": action.id,
                    "view_id": repair_card_v2_view.id,
                    "view_mode": "repair_card_v2",
                    "sequence": 2,
                })

        ordered_views = repair_card_action_view | (action.view_ids - repair_card_action_view)
        for index, action_view in enumerate(ordered_views, start=1):
            action_view.sequence = index
