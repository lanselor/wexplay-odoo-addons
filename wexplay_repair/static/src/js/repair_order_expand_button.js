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

            onMounted(() => {
                this.injectWexButton();
                const cp = document.querySelector(".o_control_panel");
                if (!cp) return;

                this._wexObserver = new MutationObserver(() => {
                    if (this._wexSelfUpdate) return;
                    this.injectWexButton();
                });
                this._wexObserver.observe(cp, { childList: true, subtree: true });
            });

            onWillUnmount(() => {
                this._wexObserver?.disconnect();
            });
        },

        // Comprobación visual para el botón
        _wexHasFoldedGroups() {
            // Buscamos si hay algún icono de "caret-right" (plegado) en la tabla
            const caret = document.querySelector(".o_group_caret.fa-caret-right, .o_group_caret.fa-chevron-right");
            return !!caret;
        },

        _wexUpdateButtonLabel() {
            if (!this._wexBtn) return;
            const hasFolded = this._wexHasFoldedGroups();
            this._wexSelfUpdate = true;
            this._wexBtn.innerHTML = hasFolded
                ? '<i class="fa fa-expand me-1"></i> Expandir'
                : '<i class="fa fa-compress me-1"></i> Plegar';
            setTimeout(() => { this._wexSelfUpdate = false; }, 0);
        },

        injectWexButton() {
            const container = document.querySelector(".o_control_panel_main_buttons") ||
                              document.querySelector(".o_cp_buttons");
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
            // 1. Decidimos qué acción hacer basándonos en si hay algo plegado
            const shouldExpand = this._wexHasFoldedGroups();
            
            // 2. Buscamos todas las cabeceras de grupo
            const headers = document.querySelectorAll("tr.o_group_header");

            headers.forEach(tr => {
                const caret = tr.querySelector(".o_group_caret");
                if (!caret) return;

                // Comprobamos si el grupo está plegado (caret a la derecha)
                const isFolded = caret.classList.contains("fa-caret-right") || 
                                 caret.classList.contains("fa-chevron-right");

                // SOLO hacemos click si el estado del grupo es el que queremos cambiar
                // (Si queremos expandir, solo clicamos los plegados. Si queremos plegar, solo los abiertos)
                if (shouldExpand === isFolded) {
                    tr.click();
                }
            });
            
            // 3. Actualizamos el botón tras un breve delay para que el DOM cambie
            setTimeout(() => this._wexUpdateButtonLabel(), 150);
        }
    });
} catch (e) {
    console.error("WEXPLAY: Error", e);
}