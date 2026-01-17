/** @odoo-module **/

console.log("WEXPLAY_PRINT: JS cargado (ByKind + qty + wizard action report)");

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

        // Estado mínimo para la cantidad
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

    // --- UI qty controls (mínimo 1) ---
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

    /**
     * Construye una URL /report/pdf/ a partir de un ir.actions.report
     * (mantiene el comportamiento estándar del cliente web para options/context).
     */
    _reportUrlFromAction(action) {
        const reportName = action?.report_name;
        const ctx = action?.context || {};

        // Docids: priorizamos active_ids/active_id; fallback a vacío (se validará)
        const ids =
            ctx.active_ids ||
            (ctx.active_id ? [ctx.active_id] : []);

        if (!reportName || !ids.length) {
            throw new Error("Acción de reporte incompleta: falta report_name o ids (active_id/active_ids).");
        }

        let url = `/report/pdf/${reportName}/${ids.join(",")}`;

        // Cuando el wizard necesita options, Odoo lo pasa por ?options=...&context=...
        if (action.data) {
            const options = encodeURIComponent(JSON.stringify(action.data));
            const context = encodeURIComponent(JSON.stringify({ ...ctx }));
            url += `?options=${options}&context=${context}`;
        }

        return this._abs(url);
    }

    async printProductLabel() {
        const productId = this._getActiveId();
        if (!productId) {
            this.notification.add("No se pudo determinar el producto actual.", { type: "danger" });
            return;
        }

        const qty = this._sanitizeQty(this.state.qty);

        try {
            // 1) Crear wizard product.label.layout (custom_quantity = qty)
            const created = await this.orm.create("product.label.layout", [
                {
                    product_tmpl_ids: [[6, 0, [productId]]],
                    print_format: "2x7xprice",
                    custom_quantity: qty,
                    move_quantity: "custom",
                },
            ]);

            const wizardId = Array.isArray(created) ? created[0] : created;

            // 2) Ejecutar process (wizard devuelve ir.actions.report con los datos correctos)
            const action = await this.orm.call("product.label.layout", "process", [[wizardId]], {
                context: {
                    active_model: "product.template",
                    active_id: productId,
                    active_ids: [productId],
                },
            });

            // 3) Si es reporte, imprimimos EL REPORTE DEL WIZARD (no uno fijo)
            if (action?.type === "ir.actions.report") {
                const reportUrl = this._reportUrlFromAction(action);

                console.log("WEXPLAY_PRINT: wizard reportUrl:", reportUrl, {
                    qty,
                    report_name: action.report_name,
                    hasData: !!action.data,
                });

                await printOdooPdfUrlByKind("label", reportUrl, this.env);

                this.notification.add(`Etiqueta enviada (${qty} uds).`, { type: "success" });
                return;
            }

            // Si no es un reporte, comportamiento estándar
            await this.actionService.doAction(action);
            this.notification.add("Etiqueta generada correctamente.", { type: "success" });
        } catch (error) {
            console.error("WEXPLAY_PRINT: error impresión", error);
            this.notification.add(`Error generando la etiqueta: ${error?.message || error}`, { type: "danger" });
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
