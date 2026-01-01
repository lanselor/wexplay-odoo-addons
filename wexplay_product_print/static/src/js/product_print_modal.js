/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class PrintCenterModal extends Component {
    setup() {
        this.dialog = useService("dialog");
        this.notification = useService("notification");
    }

    close() {
        this.props.close();
    }

    printProductLabel() {
        // Placeholder: aquí mañana conectamos QZ + PDF/ZPL
        this.notification.add(
            "Acción: Etiqueta de producto (pendiente de conectar QZ).",
            { type: "info" }
        );
    }
}
PrintCenterModal.template = "wexplay_product_print.PrintCenterModal";

// Hook: click del botón en el form (simple, sin patches complejos)
function bindPrintCenterButton(env) {
    document.addEventListener("click", (ev) => {
        const btn = ev.target.closest(".o_wexplay_open_print_center");
        if (!btn) return;

        const dialog = env.services.dialog;
        dialog.add(PrintCenterModal, {});
    });
}

// Registrar un service pequeño para tener acceso a env
registry.category("services").add("wexplay_product_print.bootstrap", {
    start(env) {
        bindPrintCenterButton(env);
        return {};
    },
});
