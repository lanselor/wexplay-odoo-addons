// wexplay_sat_print/static/src/js/repair_print_center_modal.js
/** @odoo-module **/

console.log("WEXPLAY_SAT_PRINT: modal JS cargado");

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { printOdooPdfUrl } from "@wexplay_product_print/js/qz_print";

const DEFAULT_LABEL_PRINTER = "Brother QL-710W";
const DEFAULT_TICKET_PRINTER = "Thermal 80mm"; // ajusta al nombre real en QZ

class SatPrintCenterModal extends Component {
    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        console.log("WEXPLAY_SAT_PRINT: setup ejecutado", {
            activeId: this.props.record?.resId,
        });
    }

    // Igual que en product_print: método close() que llama a this.props.close()
    close() {
        this.props.close();
    }

    // Helpers
    _abs(url) {
        return new URL(url, browser.location.origin).toString();
    }

    _reportUrl(reportName) {
        const id = this.props.record?.resId;
        return this._abs(`/report/pdf/${reportName}/${id}`);
    }

    async onPrintLabel29x90() {
        const url = this._reportUrl("wexplay_sat_print.report_repair_label_29x90");
        return this._print(url, DEFAULT_LABEL_PRINTER);
    }

    async onPrintLabel29x42() {
        const url = this._reportUrl("wexplay_sat_print.report_repair_label_29x42");
        return this._print(url, DEFAULT_LABEL_PRINTER);
    }

    async onPrintTicket80x170() {
        const url = this._reportUrl("wexplay_sat_print.report_repair_ticket_80x170");
        return this._print(url, DEFAULT_TICKET_PRINTER);
    }

    async _print(reportUrl, printerName) {
        try {
            // Reutiliza helper existente
            await printOdooPdfUrl(reportUrl, printerName);
            this.notification.add("Impresión enviada a QZ Tray.", { type: "success" });
        } catch (e) {
            console.error("WEXPLAY_SAT_PRINT: error impresión", e);
            this.notification.add(`Error imprimiendo: ${e?.message || e}`, { type: "danger" });
        }
    }
}

// Template OWL
SatPrintCenterModal.template = "wexplay_sat_print.SatPrintCenterModal";

// Action registry (MISMO patrón que product_print)
registry.category("actions").add("wexplay_sat_print.print_center", async (env, action) => {
    console.log("WEXPLAY_SAT_PRINT: handler ejecutado", { action });

    env.services.notification.add("SAT Print: acción ejecutada", { type: "info" });

    // En una orden de reparación: active_id = repair.order id
    const activeId = action?.context?.active_id;

    if (!activeId) {
        env.services.notification.add("SAT Print: no se pudo determinar la orden (active_id).", { type: "danger" });
        return;
    }

    // Igual que product_print: pasamos record con resId
    env.services.dialog.add(SatPrintCenterModal, {
        record: { resId: activeId },
    });
});

export { SatPrintCenterModal };
