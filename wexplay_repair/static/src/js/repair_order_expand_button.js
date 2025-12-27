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
                this.injectWexButton();

                // Observa SOLO el control panel (mucho más barato que document.body)
                const cp = document.querySelector(".o_control_panel");
                if (!cp) return;

                this._wexObserver = new MutationObserver(() => {
                    if (this._wexInjectScheduled) return;
                    this._wexInjectScheduled = true;
                    queueMicrotask(() => {
                        this._wexInjectScheduled = false;
                        this.injectWexButton();
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

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "btn btn-outline-primary btn-sm ms-2 border";
            btn.setAttribute("data-wex", "expand");
            btn.innerHTML = '<i class="fa fa-expand me-1"></i> Expandir';

            btn.addEventListener("click", (ev) => {
                ev.preventDefault();
                this.wexplayExpandAll();
            });

            // Después de "Nuevo" (si existe)
            if (btnNuevo && btnNuevo.nextSibling) {
                container.insertBefore(btn, btnNuevo.nextSibling);
            } else if (btnNuevo) {
                btnNuevo.insertAdjacentElement("afterend", btn); // alternativa aún más limpia
            } else {
                container.appendChild(btn);
            }
        },

        async wexplayExpandAll() {
            // En Odoo 18, el root es el que contiene la lista de grupos
            const root = this.model?.root;
            
            if (!root || !root.groups) {
                console.warn("WEXPLAY: No hay grupos para expandir.");
                return;
            }

            // Filtramos los grupos que están plegados
            const groupsToExpand = root.groups.filter(g => g.isFolded);

            for (const group of groupsToExpand) {
                try {
                    // Primero intentamos root.toggleGroup (estándar en v18)
                    if (root.toggleGroup) {
                        await root.toggleGroup(group);
                    } 
                    // Si no existe, probamos en el modelo (fallback)
                    else if (this.model.toggleGroup) {
                        await this.model.toggleGroup(group);
                    }
                } catch (e) {
                    console.error("WEXPLAY: Error expandiendo grupo", group, e);
                }
            }
        },



    });
} catch (e) {
    console.error("WEXPLAY: patch expand button failed", e);
}
