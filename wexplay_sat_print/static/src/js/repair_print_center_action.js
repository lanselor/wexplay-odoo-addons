// wexplay_sat_print/static/src/js/repair_print_center_action.js
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SatPrintCenterModal } from "./repair_print_center_modal"; // ruta relativa, mismo módulo

const ACTION_KEY = "wexplay_sat_print.print_center";

// Evita el error: "it already exists" (doble carga por assets/debug/hot reload)
const actionsRegistry = registry.category("actions");
if (!actionsRegistry.contains(ACTION_KEY)) {
    actionsRegistry.add(ACTION_KEY, async (env, action) => {
        const activeId = action?.context?.active_id;

        if (!activeId) {
            env.services.notification.add(
                "SAT Print: no se pudo determinar la orden (active_id).",
                { type: "danger" }
            );
            return;
        }

        env.services.dialog.add(SatPrintCenterModal, {
            record: { resId: activeId },
        });
    });
} else {
    console.warn(`WEXPLAY_SAT_PRINT: action '${ACTION_KEY}' ya registrada; se omite add().`);
}
