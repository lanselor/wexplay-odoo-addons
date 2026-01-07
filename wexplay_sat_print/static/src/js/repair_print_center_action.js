/** @odoo-module **/

import { registry } from "@web/core/registry";
import { RepairPrintCenterModal } from "../js/repair_print_center_modal";

registry.category("actions").add("wexplay_repair.print_center", async (env, action) => {
    const activeId = action?.context?.active_id;
    env.services.dialog.add(RepairPrintCenterModal, {
        repairId: activeId || null,
    });
});
