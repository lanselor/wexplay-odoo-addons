// wexplay_sat_print/static/src/js/repair_print_center_modal.js
/** @odoo-module **/

console.log("WEXPLAY_SAT_PRINT: modal JS cargado Versión 13 (qty accesorios)");

import { Component, useState } from "@odoo/owl";
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

        // Estado mínimo para cantidad de etiquetas de accesorios
        this.state = useState({
            accessoryQty: 1,
        });

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

    // ------------------------------
    // Qty helpers (mínimo 1)
    // ------------------------------
    _sanitizeQty(value) {
        const n = Number.parseInt(value, 10);
        if (Number.isNaN(n) || n < 1) return 1;
        return n;
    }

    onAccessoryQtyInput(ev) {
        this.state.accessoryQty = this._sanitizeQty(ev.target.value);
    }

    incrementAccessoryQty() {
        this.state.accessoryQty = this._sanitizeQty(this.state.accessoryQty + 1);
    }

    decrementAccessoryQty() {
        this.state.accessoryQty = this._sanitizeQty(this.state.accessoryQty - 1);
    }

    // ------------------------------
    // Acciones
    // ------------------------------
    async onPrintAll() {
    // Validación única (evita 3 mensajes de “no se pudo determinar…”)
        const id = this._getActiveId();
        if (!id) {
            this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            return;
        }

        try {
            // Secuencial (más estable con QZ/colas/drivers)
            await this.onPrintLabel29x90();
            await this.onPrintLabel29x42();
            await this.onPrintTicket80x170();

            this.notification.add("Impresión completa enviada a QZ Tray.", { type: "success" });
        } catch (e) {
            // Si falla una, aborta (el resto no se lanza)
            this.notification.add(`Error en "Imprimir todo": ${e?.message || e}`, { type: "danger" });
        }
    }
    
    async onPrintSat() {
    // Validación única (evita 2 mensajes de “no se pudo determinar…”)
        const id = this._getActiveId();
        if (!id) {
            this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            return;
        }

        try {
            // Secuencial (más estable con QZ/colas/drivers)
            await this.onPrintLabel29x90();
            await this.onPrintTicket80x170();

            this.notification.add("Impresión completa enviada a QZ Tray.", { type: "success" });
        } catch (e) {
            // Si falla una, aborta (el resto no se lanza)
            this.notification.add(`Error en "Imprimir todo": ${e?.message || e}`, { type: "danger" });
        }
    }

    async onPrintLabel29x90() {
        const id = this._getActiveId();
        if (!id) {
            this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            return;
        }
        // Etiqueta SAT completa: 1 copia (por ahora)
        return this._printByKind("label", this._reportUrl("wexplay_sat_print.report_repair_label_29x90"), { copies: 1 });
    }

    async onPrintLabel29x42() {
        const id = this._getActiveId();
        if (!id) {
            this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            return;
        }

        const qty = this._sanitizeQty(this.state.accessoryQty);

        // Etiqueta accesorios: aplica cantidad vía QZ copies
        return this._printByKind("label", this._reportUrl("wexplay_sat_print.report_repair_label_29x42"), { copies: qty });
    }

    async onPrintTicket80x170() {
        const id = this._getActiveId();
        if (!id) {
            this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            return;
        }
        // Ticket: thermal (copies=1 por defecto; no exponemos qty aquí)
        return this._printByKind("thermal", this._reportUrl("wexplay_sat_print.report_repair_ticket_80x170"));
    }

    // API única de impresión en el modal: todo pasa por kind
    async _printByKind(kind, reportUrl, opts = {}) {
        try {
            await printOdooPdfUrlByKind(kind, reportUrl, this.env, opts);

            // Mensaje con cantidad si aplica
            const copies = Number.isInteger(opts.copies) && opts.copies > 0 ? opts.copies : 1;
            if (kind === "label" && copies > 1) {
                this.notification.add(`Impresión enviada a QZ Tray (${copies} copias).`, { type: "success" });
            } else {
                this.notification.add("Impresión enviada a QZ Tray.", { type: "success" });
            }
        } catch (e) {
            this.notification.add(`Error imprimiendo: ${e?.message || e}`, { type: "danger" });
        }
    }
}

SatPrintCenterModal.template = "wexplay_sat_print.SatPrintCenterModal";
