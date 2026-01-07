// wexplay_sat_print/static/src/js/repair_print_center_action.js
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SatPrintCenterModal } from "wexplay_sat_print/static/src/js/repair_print_center_modal.js";


console.log("WEXPLAY_SAT_PRINT: repair_print_center_action.js cargado");

registry.category("actions").add("wexplay_sat_print.print_center", async (env, action) => {
    // active_id viene del botón type="action" en el form de repair.order
    const activeId = action?.context?.active_id;

    if (!activeId) {
        env.services.notification.add("SAT Print: no se pudo determinar la orden (active_id).", { type: "danger" });
        return;
    }

    env.services.dialog.add(SatPrintCenterModal, { activeId });
});
