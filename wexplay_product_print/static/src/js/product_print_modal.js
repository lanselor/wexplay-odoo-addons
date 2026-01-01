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
        this.notification.add("OK: botón etiqueta (sin imprimir aún).", { type: "info" });
    }
}
PrintCenterModal.template = "wexplay_product_print.PrintCenterModal";

registry.category("actions").add("wexplay_product_print.print_center", async (env) => {
    console.log("WEXPLAY_PRINT: handler ejecutado");
    env.services.notification.add("Wexplay Print: acción ejecutada", { type: "info" });

    const close = env.services.dialog.add(PrintCenterModal, {
        close: null, // placeholder, lo reescribimos abajo
    });

    // En algunas versiones add() devuelve una función close, en otras un id.
    // Para hacerlo universal, volvemos a abrir de forma simple:
});
