/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";

try {
    patch(ListController.prototype, {
        setup() {
            super.setup();

            // Limitar al modelo
            if (this.props?.resModel !== "repair.order") return;

            this._wexObserver = null;
            this._wexInjectScheduled = false;

        onMounted(() => {
            try { this.injectWexButton(); } catch (e) { console.error("WEXPLAY inject failed", e); }

            const cp = document.querySelector(".o_control_panel");
            if (!cp) return;

            this._wexObserver = new MutationObserver(() => {
                if (this._wexInjectScheduled) return;
                this._wexInjectScheduled = true;
                queueMicrotask(() => {
                    this._wexInjectScheduled = false;
                    try { this.injectWexButton(); } catch (e) { console.error("WEXPLAY inject failed", e); }
                });
            });

            this._wexObserver.observe(cp, { childList: true, subtree: true });
        });


         onWillUnmount(() => {
                this._wexObserver?.disconnect();
                this._wexObserver = null;
            });
        },

        injectWexButton() {
            const container =
                document.querySelector(".o_control_panel .o_control_panel_main_buttons") ||
                document.querySelector(".o_control_panel .o_cp_buttons");

            if (!container || container.querySelector("[data-wex='expand']")) return;

            // Localizar "Nuevo" dentro del contenedor
            const btnNuevo =
                container.querySelector("button.o_list_button_add") ||
                container.querySelector("button.o_list_button_create") ||
                null;

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "btn btn-outline-primary btn-sm ms-2 border";
            btn.setAttribute("data-wex", "expand");
            btn.innerHTML = '<i class="fa fa-expand me-1"></i> Expandir';

            btn.addEventListener("click", (ev) => {
                ev.preventDefault();
                this.wexplayExpandAll();
            });

            // Insertar justo después de "Nuevo" si existe
            if (btnNuevo) {
                btnNuevo.insertAdjacentElement("afterend", btn);
            } else {
                container.appendChild(btn);
            }
        },

        async wexplayExpandAll() {
            // Cada header de grupo plegado
            const headers = document.querySelectorAll(
                "tr.o_group_has_content.o_group_header"
            );

            let expanded = 0;

            headers.forEach(tr => {
                const caret = tr.querySelector(".o_group_caret");

                // Si el caret está apuntando a la derecha → está plegado
                if (caret && caret.classList.contains("fa-caret-right")) {
                    tr.click();   // MISMO click que el usuario
                    expanded++;
                }
            });

            console.warn("WEXPLAY: grupos expandidos:", expanded);
        }



    });
} catch (e) {
    console.error("WEXPLAY: patch expand button failed", e);
}
