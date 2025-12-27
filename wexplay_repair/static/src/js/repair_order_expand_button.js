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
            this._wexObserver = null;
            this._wexInjectScheduled = false;

            // Limitar al modelo
            if (this.props?.resModel !== "repair.order") return;

            onMounted(() => {
                try {
                    this.injectWexButton();
                } catch (e) {
                    console.error("WEXPLAY inject failed", e);
                }

                const cp = document.querySelector(".o_control_panel");
                if (!cp) return;

                this._wexObserver = new MutationObserver(() => {
                    // Evitar bucles por cambios que hacemos nosotros (innerHTML)
                    if (this._wexSelfUpdate) return;

                    // Throttle para no ejecutar cientos de veces por render
                    if (this._wexInjectScheduled) return;
                    this._wexInjectScheduled = true;

                    queueMicrotask(() => {
                        this._wexInjectScheduled = false;
                        try {
                            this.injectWexButton();
                        } catch (e) {
                            console.error("WEXPLAY inject failed", e);
                        }
                    });
                });

                this._wexObserver.observe(cp, { childList: true, subtree: true });
            });

            onWillUnmount(() => {
                this._wexObserver?.disconnect();
                this._wexObserver = null;
                this._wexBtn = null;
            });
        },

        // ¿Hay al menos un grupo plegado? (caret a la derecha)
        _wexHasFoldedGroups() {
            return !!document.querySelector(
                "tr.o_group_header .o_group_caret.fa-caret-right, " +
                "tr.o_group_header .o_group_caret.fa-chevron-right"
            );
        },

        _wexUpdateButtonLabel() {
            if (!this._wexBtn) return;

            console.warn("WEXPLAY label check:", {
            hasFolded: this._wexHasFoldedGroups(),
            sampleCaret: document.querySelector(".o_group_caret")?.className,
            });



            const hasFolded = this._wexHasFoldedGroups();

            // Marcar actualización propia para que el observer la ignore
            this._wexSelfUpdate = true;

            this._wexBtn.innerHTML = hasFolded
                ? '<i class="fa fa-expand me-1"></i> Expandir'
                : '<i class="fa fa-compress me-1"></i> Plegar';

            // Liberar flag en el siguiente tick
            setTimeout(() => {
                this._wexSelfUpdate = false;
            }, 0);
        },

        injectWexButton() {
            const container =
                document.querySelector(".o_control_panel_main_buttons") ||
                document.querySelector(".o_control_panel .o_control_panel_main_buttons") ||
                document.querySelector(".o_cp_buttons") ||
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

            btn.addEventListener("click", (ev) => {
                ev.preventDefault();
                this.wexHandleClick();
            });

            // Insertar después de "Nuevo" si existe; si no, al final
            const btnNuevo =
                container.querySelector("button.o_list_button_add") ||
                container.querySelector("button.o_list_button_create") ||
                null;

            if (btnNuevo) {
                btnNuevo.insertAdjacentElement("afterend", btn);
            } else {
                container.appendChild(btn);
            }

            this._wexBtn = btn;
            this._wexUpdateButtonLabel();
        },

        async wexHandleClick() {
            // Acción global:
            // - Si hay alguno cerrado => EXPANDIR (solo cerrados)
            // - Si no hay cerrados => PLEGAR (solo abiertos)
            const isExpandingAction = this._wexHasFoldedGroups();

            const headers = document.querySelectorAll(
                "tr.o_group_has_content.o_group_header"
            );

            headers.forEach((tr) => {
                const caret = tr.querySelector(".o_group_caret");
                if (!caret) return;

                const isFolded =
                    caret.classList.contains("fa-caret-right") ||
                    caret.classList.contains("fa-chevron-right");

                if (isExpandingAction && isFolded) {
                    tr.click();
                } else if (!isExpandingAction && !isFolded) {
                    tr.click();
                }
            });

            // Refrescar etiqueta tras render (doble tick, más fiable)
            setTimeout(() => this._wexUpdateButtonLabel(), 0);
            setTimeout(() => this._wexUpdateButtonLabel(), 100);
        },
    });
} catch (e) {
    console.error("WEXPLAY Error:", e);
}
