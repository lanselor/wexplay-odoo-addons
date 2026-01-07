// wexplay_sat_print/static/src/js/repair_print_center_modal.js
/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { printOdooPdfUrl } from "wexplay_product_print/static/src/js/qz_print.js";


// Reutilizamos EXACTAMENTE el helper existente (no se modifica)
import { printOdooPdfUrl } from "wexplay_product_print/static/src/js/qz_print";

const DEFAULT_LABEL_PRINTER = "Brother QL-710W";
const DEFAULT_TICKET_PRINTER = "Thermal 80mm"; // ajusta al nombre real en tu sistema QZ

export class SatPrintCenterModal extends Component {
    static template = "wexplay_sat_print.SatPrintCenterModal";
    static props = {
        activeId: { type: Number },
    };

    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    }

    // Helpers
    _abs(url) {
        return new URL(url, browser.location.origin).toString();
    }

    _reportUrl(reportName) {
        // Odoo estándar: /report/pdf/<report_name>/<id>
        return this._abs(`/report/pdf/${reportName}/${this.props.activeId}`);
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
            await printOdooPdfUrl(reportUrl, printerName);
            this.notification.add("Impresión enviada a QZ Tray.", { type: "success" });
        } catch (e) {
            this.notification.add(`Error imprimiendo: ${e?.message || e}`, { type: "danger" });
        }
    }

    onClose() {
        // Cierra el modal
        this.props.close?.();
    }
}
