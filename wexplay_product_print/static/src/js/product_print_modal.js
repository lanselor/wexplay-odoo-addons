/** @odoo-module **/

console.log("WEXPLAY_PRINT: JS cargado (ByKind + qty) - custom report");

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { printOdooPdfUrlByKind } from "@wexplay_product_print/js/qz_print";

class PrintCenterModal extends Component {
    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialog = useService("dialog");

        this.state = useState({ qty: 1 });

        console.log("WEXPLAY_PRINT: setup ejecutado", {
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

    _sanitizeQty(value) {
        const n = Number.parseInt(value, 10);
        if (Number.isNaN(n) || n < 1) return 1;
        return n;
    }

    onQtyInput(ev) {
        this.state.qty = this._sanitizeQty(ev.target.value);
    }

    incrementQty() {
        this.state.qty = this._sanitizeQty(this.state.qty + 1);
    }

    decrementQty() {
        this.state.qty = this._sanitizeQty(this.state.qty - 1);
    }

    async printProductLabel() {
        const productId = this._getActiveId();
        if (!productId) {
            this.notification.add("No se pudo determinar el producto actual.", { type: "danger" });
            return;
        }

        const qty = this._sanitizeQty(this.state.qty);

        try {
            // Reporte custom (control total del layout)
            const reportName = "wexplay_product_print.report_product_label_ql700_62x29";
            const reportUrl = this._reportUrl(reportName);

            // Imprimir por tipo (label): el core resuelve impresora desde Ajustes
            await printOdooPdfUrlByKind("label", reportUrl, this.env);

            // Nota: de momento qty solo afecta a UI; el siguiente paso será aplicarlo (QZ copies o QWeb).
            this.notification.add(`Etiqueta enviada. (Cantidad seleccionada: ${qty})`, { type: "success" });
        } catch (error) {
            console.error("WEXPLAY_PRINT: error impresión", error);
            this.notification.add(`Error imprimiendo la etiqueta: ${error?.message || error}`, { type: "danger" });
        }
    }
}

PrintCenterModal.template = "wexplay_product_print.PrintCenterModal";

registry.category("actions").add("wexplay_product_print.print_center", async (env, action) => {
    console.log("WEXPLAY_PRINT: handler ejecutado");

    env.services.notification.add("Wexplay Print: acción ejecutada", { type: "info" });

    const activeId = action?.context?.active_id;

    env.services.dialog.add(PrintCenterModal, {
        record: activeId ? { resId: activeId } : null,
    });
});
