// wexplay_sat_print/static/src/js/repair_print_center_modal.js
/** @odoo-module **/

console.log("WEXPLAY_SAT_PRINT: modal JS cargado Versión 12");

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { printOdooPdfUrlByKind } from "@wexplay_product_print/js/qz_print";

// NOTA: mantenemos estas constantes por compatibilidad temporal,
// pero ya no se usan cuando migramos todo a ByKind.
const DEFAULT_LABEL_PRINTER = "Brother QL-710W";
const DEFAULT_TICKET_PRINTER = "Thermal 80mm";

export class SatPrintCenterModal extends Component {
    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialog = useService("dialog");

        console.log("WEXPLAY_SAT_PRINT: setup ejecutado", {
            hasClose: !!this.props?.close,
            record: this.props?.record,
        });
        console.log("WEXPLAY_SAT_PRINT: setup ejecutado", {
            orm: this.orm,
            hasOrmCall: !!this.orm?.call,
        });
    }

    close() {
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
        return this._printByKind("label", this._reportUrl("wexplay_sat_print.report_repair_label_29x90"));
    }

    async onPrintLabel29x42() {
        const id = this._getActiveId();
        if (!id) {
            this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            return;
        }
        // Migrado a ByKind
        return this._printByKind("label", this._reportUrl("wexplay_sat_print.report_repair_label_29x42"));
    }

    async onPrintTicket80x170() {
        const id = this._getActiveId();
        if (!id) {
            this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            return;
        }
        // Migrado a ByKind
        return this._printByKind("thermal", this._reportUrl("wexplay_sat_print.report_repair_ticket_80x170"));
    }

    // API única de impresión en el modal: todo pasa por kind
    async _printByKind(kind, reportUrl) {
        try {
            await printOdooPdfUrlByKind(kind, reportUrl, this.env);
            this.notification.add("Impresión enviada a QZ Tray.", { type: "success" });
        } catch (e) {
            this.notification.add(`Error imprimiendo: ${e?.message || e}`, { type: "danger" });
        }
    }
}

SatPrintCenterModal.template = "wexplay_sat_print.SatPrintCenterModal";
