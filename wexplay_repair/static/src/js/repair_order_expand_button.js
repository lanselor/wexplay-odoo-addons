/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(ListController.prototype, {
    setup() {
        super.setup?.();

        // Servicio de notificaciones (toast)
        this.notification = useService("notification");

        // Limitar SOLO a la lista con js_class="wex_repair_list"
        const jsClass = this.props?.archInfo?.jsClass;
        if (jsClass !== "wex_repair_list") {
            return;
        }

        onMounted(() => {
            // Intenta localizar la zona de botones de la lista
            const buttons = this.el?.querySelector(".o_list_buttons");
            if (!buttons) {
                console.warn("WEXPLAY: no encuentro .o_list_buttons");
                return;
            }

            // Evitar duplicados si Odoo re-monta la vista
            if (buttons.querySelector('[data-wex="test-btn"]')) {
                return;
            }

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "btn btn-primary";
            btn.textContent = "Mi botón (JS)";
            btn.setAttribute("data-wex", "test-btn");

            btn.addEventListener("click", () => {
                console.log("WEXPLAY: click en Mi botón (JS)");
                this.notification.add("Botón JS pulsado (prueba OK)", { type: "info" });
            });

            // Inserta el botón en la barra (junto al resto)
            buttons.appendChild(btn);

            console.log("WEXPLAY: botón JS inyectado en la lista");
        });
    },
});
