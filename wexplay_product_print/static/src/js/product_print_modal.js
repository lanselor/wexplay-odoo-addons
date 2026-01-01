/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

console.log("WEXPLAY: product_print_modal cargado");
class PrintCenterModal extends Component {
    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    }

    onClose() {
        this.dialog.close();
    }

    printProductLabel() {
        this.notification.add(
            "Acción: Etiqueta de producto (pendiente de conectar QZ).",
            { type: "info" }
        );
    }
}
PrintCenterModal.template = "wexplay_product_print.PrintCenterModal";

/**
 * Client Action que lanza el modal.
 * Odoo ejecuta esto cuando el botón llama al ir.actions.client con tag.
 */
class PrintCenterClientAction extends Component {
    setup() {
        this.dialog = useService("dialog");
    }
    async onMounted() {
        this.dialog.add(PrintCenterModal, {});
    }
}
PrintCenterClientAction.template = "owl.Empty";

// Registro de la client action (clave = tag del ir.actions.client)
registry.category("actions").add("wexplay_product_print.print_center", {
    component: PrintCenterClientAction,
});
