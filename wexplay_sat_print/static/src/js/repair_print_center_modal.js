// wexplay_sat_print/static/src/js/repair_print_center_modal.js
/** @odoo-module **/

console.log("WEXPLAY_SAT_PRINT: modal JS cargado");

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { printOdooPdfUrl } from "@wexplay_product_print/js/qz_print";

const DEFAULT_LABEL_PRINTER = "Brother QL-710W";
const DEFAULT_TICKET_PRINTER = "Thermal 80mm";

export class SatPrintCenterModal extends Component {
    setup() {
        this.notification = useService("notification");

        console.log("WEXPLAY_SAT_PRINT: setup ejecutado", {
            hasClose: !!this.props?.close,
            record: this.props?.record,
        });
    }

    close() {
        // Igual que en product_print_modal.js
        this.props.close();
    }

    _abs(url) {
        return new URL(url, browser.location.origin).toString();
    }

    _getActiveId() {
        return this.props.record?.resId;
    }

    _reportUrl(reportName) {
        const id = this._getActiveId();
        return this._abs(`/report/pdf/${reportName}/${id}`);
    }

    async onPrintLabel29x90() {
        const id = this._getActiveId();
        if (!id) {
            this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            return;
        }
        return this._print(this._reportUrl("wexplay_sat_print.report_repair_label_29x90"), DEFAULT_LABEL_PRINTER);
    }

    async onPrintLabel29x42() {
        const id = this._getActiveId();
        if (!id) {
            this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            return;
        }
        return this._print(this._reportUrl("wexplay_sat_print.report_repair_label_29x42"), DEFAULT_LABEL_PRINTER);
    }

    async onPrintTicket80x170() {
        const id = this._getActiveId();
        if (!id) {
            this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            return;
        }
        return this._print(this._reportUrl("wexplay_sat_print.report_repair_ticket_80x170"), DEFAULT_TICKET_PRINTER);
    }

    async _print(reportUrl, printerName) {
        try {
            await printOdooPdfUrl(reportUrl, printerName);
            this.notification.add("Impresión enviada a QZ Tray.", { type: "success" });
        } catch (e) {
            this.notification.add(`Error imprimiendo: ${e?.message || e}`, { type: "danger" });
        }
    }
}

SatPrintCenterModal.template = "wexplay_sat_print.SatPrintCenterModal";
