/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";

try {
    patch(ListController.prototype, {
        setup() {
            super.setup();
            
            this._wexBtn = null;
            this._wexSelfUpdate = false;

            if (this.props?.resModel !== "repair.order") return;

            this._wexObserver = null;
            this._wexInjectScheduled = false;

            onMounted(() => {
                this.injectWexButton();
                const cp = document.querySelector(".o_control_panel");
                if (!cp) return;

                this._wexObserver = new MutationObserver(() => {
                    if (this._wexSelfUpdate || this._wexInjectScheduled) return;
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

        // Comprobación basada en el MODELO (más fiable que el DOM)
        _wexHasFoldedGroups() {
            const root = this.model?.root;
            if (!root || !root.groups) return false;
            // Si hay al menos un grupo plegado, devolvemos true
            return root.groups.some(g => g.isFolded);
        },

        _wexUpdateButtonLabel() {
            if (!this._wexBtn) return;

            const hasFolded = this._wexHasFoldedGroups();
            this._wexSelfUpdate = true;

            // Actualizamos el texto y el icono según el estado
            this._wexBtn.innerHTML = hasFolded
                ? '<i class="fa fa-expand me-1"></i> Expandir'
                : '<i class="fa fa-compress me-1"></i> Plegar';

            setTimeout(() => { this._wexSelfUpdate = false; }, 0);
        },

        injectWexButton() {
            const container = document.querySelector(".o_control_panel .o_control_panel_main_buttons") ||
                              document.querySelector(".o_control_panel .o_cp_buttons");

            if (!container) return;

            const existing = container.querySelector("[data-wex='expand']");
            if (existing) {
                this._wexBtn = existing;
                this._wexUpdateButtonLabel();
                return;
            }

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "btn btn-outline-primary btn-sm ms-2 border";
            btn.setAttribute("data-wex", "expand");

            btn.onclick = (ev) => {
                ev.preventDefault();
                this.wexHandleClick();
            };

            container.appendChild(btn);
            this._wexBtn = btn;
            this._wexUpdateButtonLabel();
        },

        async wexHandleClick() {
            const root = this.model?.root;
            if (!root || !root.groups) return;

            const hasFolded = this._wexHasFoldedGroups();
            
            // Lógica inteligente: 
            // Si hay alguno cerrado -> Abrimos TODOS.
            // Si están todos abiertos -> Cerramos TODOS.
            const groupsToProcess = root.groups.filter(g => g.isFolded === hasFolded);

            for (const group of groupsToProcess) {
                try {
                    // Usamos el método nativo del root para evitar errores de Proxy
                    await root.toggleGroup(group);
                } catch (e) {
                    console.error("WEXPLAY: Error toggling group", e);
                }
            }
            
            // Esperamos un pequeño tick para que el estado del modelo se estabilice antes de cambiar la etiqueta
            setTimeout(() => this._wexUpdateButtonLabel(), 100);
        }
    });
} catch (e) {
    console.error("WEXPLAY: patch expand button failed", e);
}