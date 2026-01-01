/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class PrintCenterModal extends Component {
    setup() {
        this.notification = useService("notification");
    }
    close() {
        this.props.close();
    }
    printProductLabel() {
        this.notification.add(
            "Acción: Etiqueta de producto (pendiente de conectar QZ).",
            { type: "info" }
        );
    }
}
PrintCenterModal.template = "wexplay_product_print.PrintCenterModal";

// Client action handler: abre el modal
registry.category("actions").add("wexplay_product_print.print_center", (env) => {
    env.services.dialog.add(PrintCenterModal, {});
});
