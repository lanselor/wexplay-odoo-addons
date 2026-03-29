// wexplay_sat_print/static/src/js/qz_print_client_action.js
/** @odoo-module **/

console.log("WEXPLAY_SAT_PRINT: QZ client action (headless) cargado");

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { printOdooDocument } from "@wex_print_core/js/qz_print";

/**
 * Convierte /report/pdf/<report>/<id> a URL absoluta
 */
function abs(url) {
    return new URL(url, browser.location.origin).toString();
}

/**
 * Client Action headless:
 * - NO abre modal
 * - imprime SAT (label 29x90 + ticket 80x170) vía QZ
 *
 * Espera action.params = { resId: <int> }
 */
async function wexQzPrintSat(env, action) {
    const notification = env.services.notification;

    const resId = action?.params?.resId;
    if (!resId) {
        notification.add("No se pudo determinar la orden de reparación (resId).", { type: "danger" });
        return;
    }

    // URLs de report (igual que en tu modal)
    const urlLabel29x90 = abs(`/report/pdf/wexplay_sat_print.report_repair_label_29x90/${resId}`);
    const urlTicket80x170 = abs(`/report/pdf/wexplay_sat_print.report_repair_ticket_80x170/${resId}`);

    try {
        // Secuencial = más estable con colas/drivers
        await printOdooDocument("sat_label_main", urlLabel29x90, env, {
            copies: 1,
            reportName: "wexplay_sat_print.report_repair_label_29x90",
        });
        await printOdooDocument("sat_ticket", urlTicket80x170, env, {
            reportName: "wexplay_sat_print.report_repair_ticket_80x170",
        });

        notification.add("Impresión SAT enviada a QZ Tray.", { type: "success" });
    } catch (e) {
        notification.add(`Error imprimiendo SAT: ${e?.message || e}`, { type: "danger" });
    }
}

// IMPORTANTE: este tag debe coincidir con el que devuelve Python
registry.category("actions").add("wexplay_sat_print.qz_print_sat", wexQzPrintSat);
