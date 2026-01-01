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
    onClose() {
        this.dialog.close();
    }
    printProductLabel() {
        this.notification.add("OK: botón etiqueta (sin imprimir aún).", { type: "info" });
    }
}

// CAMBIO: template nuevo
PrintCenterModal.template = "wexplay_product_print.PrintCenterModalV2";

registry.category("actions").add("wexplay_product_print.print_center", async (env) => {
    env.services.dialog.add(PrintCenterModal, {});
    // no devolver nada
});
