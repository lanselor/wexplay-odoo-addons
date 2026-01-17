/** @odoo-module **/

console.log("WEXPLAY_PRINT: JS cargado (ByKind)");

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";

// Usamos el core único (fuente de verdad) desde el alias público del módulo
import { printOdooPdfUrlByKind } from "@wexplay_product_print/js/qz_print";

class PrintCenterModal extends Component {
    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialog = useService("dialog");

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

    async printProductLabel() {
        const productId = this._getActiveId();
        if (!productId) {
            this.notification.add("No se pudo determinar el producto actual.", { type: "danger" });
            return;
        }

        try {
            // 1) Crear wizard product.label.layout (mantenemos tu flujo intacto)
            const created = await this.orm.create("product.label.layout", [
                {
                    product_tmpl_ids: [[6, 0, [productId]]],
                    print_format: "2x7xprice",
                    custom_quantity: 1,
                    move_quantity: "custom",
                },
            ]);

            const wizardId = Array.isArray(created) ? created[0] : created;

            // 2) Ejecutar process (mantenemos tu flujo)
            const action = await this.orm.call("product.label.layout", "process", [[wizardId]], {
                context: {
                    active_model: "product.template",
                    active_id: productId,
                    active_ids: [productId],
                },
            });

            // 3) Si devuelve reporte, imprimimos por ByKind (label)
            if (action?.type === "ir.actions.report") {
                const reportName = "wexplay_product_print.report_product_label_ql700_62x29";
                const reportUrl = this._reportUrl(reportName);

                console.log("WEXPLAY_PRINT reportUrl:", reportUrl, { reportName, productId });

                await printOdooPdfUrlByKind("label", reportUrl, this.env);

                this.notification.add("Etiqueta enviada a QZ correctamente.", { type: "success" });
                return;
            }

            // 4) Si no es reporte, ejecutamos acción estándar (sin cambios)
            await this.actionService.doAction(action);
            this.notification.add("Etiqueta generada correctamente.", { type: "success" });
        } catch (error) {
            console.error("WEXPLAY_PRINT: error impresión", error);
            this.notification.add(`Error generando la etiqueta: ${error?.message || error}`, { type: "danger" });
        }
    }

    async printTestQz() {
        // Mantenemos el test, pero lo hacemos pasar por ByKind para validar config real
        const productId = this._getActiveId();
        if (!productId) {
            this.notification.add("No se pudo determinar el producto actual.", { type: "danger" });
            return;
        }
        try {
            const reportName = "wexplay_product_print.report_product_label_ql700_62x29";
            const reportUrl = this._reportUrl(reportName);

            await printOdooPdfUrlByKind("label", reportUrl, this.env);

            this.notification.add("QZ: trabajo de prueba enviado por ByKind (label).", { type: "success" });
        } catch (error) {
            console.error("WEXPLAY_PRINT: error QZ test", error);
            this.notification.add(
                `QZ: error enviando por ByKind. ${error?.message || error}`,
                { type: "danger" }
            );
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
