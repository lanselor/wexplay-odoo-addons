/** @odoo-module **/

console.log("WEXPLAY_PRINT: JS cargado");

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class PrintCenterModal extends Component {
    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    }
    close() {
        this.props.close();
    }
    printProductLabel() {
        const productId = this.props.record?.resId;

        if (!productId) {
            this.notification.add(
                "No se pudo determinar el producto actual.",
                { type: "danger" }
            );
            return;
        }

        const reportName = "product.report_producttemplatelabel2x7";
        const url = `/report/pdf/${reportName}/${productId}`;

        console.log("WEXPLAY_PRINT: abriendo PDF", url);

        // Fase 1: abrir el PDF (validación)
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
