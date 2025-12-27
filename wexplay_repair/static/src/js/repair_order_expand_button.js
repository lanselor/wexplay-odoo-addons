/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";

console.warn("WEXPLAY: expand button baseline OK (2025-12-27)");

try {
    patch(ListController.prototype, {
        setup() {
            super.setup();
            
            this._wexBtn = null;
            this._wexSelfUpdate = false;
            // Limitar al modelo
            if (this.props?.resModel !== "repair.order") return;

            this._wexObserver = null;
            this._wexInjectScheduled = false;

        onMounted(() => {
            try { this.injectWexButton(); } catch (e) { console.error("WEXPLAY inject failed", e); }

            const cp = document.querySelector(".o_control_panel");
            if (!cp) return;

            this._wexObserver = new MutationObserver(() => {
                if (this._wexSelfUpdate) return;
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

        _wexHasFoldedGroups() {
            const headers = document.querySelectorAll("tr.o_group_has_content.o_group_header");
            return Array.from(headers).some(tr =>
                tr.querySelector(".o_group_caret")?.classList.contains("fa-caret-right")
            );
        },

        _wexUpdateButtonLabel() {
            if (!this._wexBtn) return;

            const hasFolded = this._wexHasFoldedGroups();

            // Flag para que el observer ignore esta mutación
            this._wexSelfUpdate = true;

            this._wexBtn.innerHTML = hasFolded
                ? '<i class="fa fa-expand me-1"></i> Expandir'
                : '<i class="fa fa-compress me-1"></i> Plegar';

            // Liberar flag en el siguiente tick
            setTimeout(() => { this._wexSelfUpdate = false; }, 0);
        },



        injectWexButton() {
            const container =
                document.querySelector(".o_control_panel .o_control_panel_main_buttons") ||
                document.querySelector(".o_control_panel .o_cp_buttons");

            if (!container) return;

            // Si ya existe, solo referencia y sal (NO tocar innerHTML aquí)
            const existing = container.querySelector("[data-wex='expand']");
            if (existing) {
                this._wexBtn = existing;
                return;
            }

            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "btn btn-outline-primary btn-sm ms-2 border";
            btn.setAttribute("data-wex", "expand");

            btn.addEventListener("click", (ev) => {
                ev.preventDefault();
                this.wexplayExpandAll();
            });

            container.appendChild(btn);
            this._wexBtn = btn;

            // Etiqueta inicial (la ponemos UNA vez al crear)
            this._wexUpdateButtonLabel();
        },


        async wexplayExpandAll() {
            const headers = document.querySelectorAll(
                "tr.o_group_has_content.o_group_header"
            );

            let folded = 0;
            let expanded = 0;

            headers.forEach(tr => {
                const caret = tr.querySelector(".o_group_caret");
                if (!caret) return;

                const isFolded = caret.classList.contains("fa-caret-right");

                if (isFolded) {
                    tr.click();
                    expanded++;
                } else {
                    tr.click();
                    folded++;
                }
            });
            
            setTimeout(() => this._wexUpdateButtonLabel(), 0);  
            console.warn("WEXPLAY:", { expanded, folded });
        }


        



    });
} catch (e) {
    console.error("WEXPLAY: patch expand button failed", e);
}
