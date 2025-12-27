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

        // Comprobación robusta de si hay grupos plegados
        _wexHasFoldedGroups() {
            // Buscamos cualquier caret que apunte a la derecha (cerrado)
            // Odoo 18 usa fa-caret-right o fa-chevron-right
            const foldedCaret = document.querySelector(".o_group_header .o_group_caret.fa-caret-right, .o_group_header .o_group_caret.fa-chevron-right");
            return !!foldedCaret;
        },

        _wexUpdateButtonLabel() {
            if (!this._wexBtn) return;
            const hasFolded = this._wexHasFoldedGroups();
            
            this._wexSelfUpdate = true;
            if (hasFolded) {
                this._wexBtn.innerHTML = '<i class="fa fa-expand me-1"></i> Expandir';
            } else {
                this._wexBtn.innerHTML = '<i class="fa fa-compress me-1"></i> Plegar';
            }
            
            // Liberamos el flag tras el cambio de DOM
            setTimeout(() => { this._wexSelfUpdate = false; }, 50);
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
            // 1. Determinamos la acción global basándonos en si hay ALGO cerrado
            const isExpandingAction = this._wexHasFoldedGroups();
            
            const headers = document.querySelectorAll("tr.o_group_header");

            headers.forEach(tr => {
                const caret = tr.querySelector(".o_group_caret");
                if (!caret) return;

                const isFolded = caret.classList.contains("fa-caret-right") || 
                                 caret.classList.contains("fa-chevron-right");

                // LOGICA UNIDIRECCIONAL:
                // Si la acción es EXPANDIR, solo clickamos los que están CERRADOS.
                // Si la acción es PLEGAR, solo clickamos los que están ABIERTOS.
                if (isExpandingAction && isFolded) {
                    tr.click();
                } else if (!isExpandingAction && !isFolded) {
                    tr.click();
                }
            });
            
            // Esperamos a que Odoo procese los clics antes de actualizar el nombre del botón
            setTimeout(() => {
                this._wexUpdateButtonLabel();
            }, 300);
        }
    });
} catch (e) {
    console.error("WEXPLAY Error:", e);
}