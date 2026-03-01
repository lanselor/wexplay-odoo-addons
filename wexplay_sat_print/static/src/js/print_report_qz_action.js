// wexplay_sat_print/static/src/js/print_report_qz_action.js
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { printOdooPdfUrlByKind } from "@wexplay_product_print/js/qz_print";

function abs(url) {
    return new URL(url, browser.location.origin).toString();
}

function buildReportUrl(reportName, resId) {
    return abs(`/report/pdf/${reportName}/${resId}`);
}

/**
 * Acción genérica para imprimir cualquier reporte QWeb por QZ
 * Espera:
 *  params = {
 *      kind: "a4" | "label" | "thermal",
 *      report_name: "module.report_name",
 *      res_id: int
 *  }
 */
registry.category("actions").add("wexplay_sat_print.print_report_qz", async (env, action) => {
    const notification = env.services.notification;
    const { kind, report_name, res_id } = action.params || {};

    if (!kind || !report_name || !res_id) {
        notification.add("Parámetros de impresión inválidos.", { type: "danger" });
        return;
    }

    try {
        const url = buildReportUrl(report_name, res_id);
        await printOdooPdfUrlByKind(kind, url, env);
        notification.add("Impresión enviada a QZ Tray.", { type: "success" });
    } catch (e) {
        notification.add(`Error imprimiendo: ${e?.message || e}`, { type: "danger" });
    }
});