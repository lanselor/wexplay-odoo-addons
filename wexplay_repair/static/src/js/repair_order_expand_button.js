/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

console.warn("WEXPLAY: módulo JS cargado (repair_order_expand_button)");

patch(ListController.prototype, {
    setup() {
        super.setup();

        // 1) Confirmación de que el controller se está parchando
        console.warn("WEXPLAY: ListController.setup ejecutado");

        // 2) Servicio de notificaciones
        this.notification = useService("notification");

        // 3) Ver qué js_class llega realmente
        const jsClass =
            this.props?.archInfo?.jsClass ||
            this.props?.archInfo?.arch?.attrs?.js_class ||
            null;

        console.warn("WEXPLAY: jsClass detectado =", jsClass);

        // 4) Limita SOLO a tu vista si coincide (ajústalo cuando veas el valor real)
        if (jsClass !== "wex_repair_list") {
            return;
        }

        onMounted(() => {
            // Selectores típicos en Odoo 18 (dependen del layout)
            const containers = [
                ".o_list_buttons",
                ".o_control_panel .o_cp_buttons",
                ".o_control_panel .o_cp_action_menus",
            ];

            let host = null;
            for (const sel of containers) {
                host = this.el?.querySelector(sel) || document.querySelector(sel);
                if (host) break;
            }

            if (!host) {
                console.warn("WEXPLAY: no encuentro contenedor de botones");
                return;
            }

            if (host.querySelector('[data-wex="test-btn"]')) return;

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "btn btn-primary";
            btn.textContent = "Mi botón (JS)";
            btn.setAttribute("data-wex", "test-btn");

            btn.addEventListener("click", () => {
                console.log("WEXPLAY: click Mi botón (JS)");
                this.notification.add("Botón JS pulsado (OK)", { type: "info" });
            });

            host.appendChild(btn);
            console.warn("WEXPLAY: botón JS inyectado");
        });
    },
});
