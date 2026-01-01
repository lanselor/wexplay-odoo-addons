/** @odoo-module **/

console.log("WEXPLAY_PRINT: JS cargado");

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class PrintCenterModal extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    }
    close() {
        this.props.close();
    }
    async printProductLabel() {
        const productId = this.props.record?.resId;
        if (!productId) {
            this.notification.add("No se pudo determinar el producto actual.", { type: "danger" });
            return;
        }

        // Reporte técnico que encontraste
        const reportXmlName = "product.report_producttemplatelabel2x7";

        // Pedimos a Odoo la acción del reporte (como hace el sistema)
        const action = await this.rpc("/web/dataset/call_kw/ir.actions.report/get_action", {
            model: "ir.actions.report",
            method: "get_action",
            args: [
                [productId],          // ids
                reportXmlName,        // report_name técnico
            ],
            kwargs: {
                context: {
                    active_model: "product.template",
                    active_ids: [productId],
                    active_id: productId,
                },
            },
        });

        // action suele traer report_type, report_name y sobre todo una URL
        const url = action?.url || action?.report_url;
        if (!url) {
            console.log("WEXPLAY_PRINT: acción devuelta sin url", action);
            this.notification.add("No se pudo generar la URL del reporte.", { type: "danger" });
            return;
        }

        console.log("WEXPLAY_PRINT: abriendo PDF", url);
        window.open(url, "_blank");
        this.notification.add("OK: botón etiqueta (sin imprimir aún).", { type: "info" });
    }     

}

PrintCenterModal.template = "wexplay_product_print.PrintCenterModal";

registry.category("actions").add("wexplay_product_print.print_center", async (env, action) => {
    console.log("WEXPLAY_PRINT: handler ejecutado");

    env.services.notification.add("Wexplay Print: acción ejecutada", { type: "info" });

    // active_id viene del botón type="action" en la vista del producto
    const activeId = action?.context?.active_id;

    env.services.dialog.add(PrintCenterModal, {
        record: activeId ? { resId: activeId } : null,
    });

    // En algunas versiones add() devuelve una función close, en otras un id.
    // Para hacerlo universal, volvemos a abrir de forma simple:
});
