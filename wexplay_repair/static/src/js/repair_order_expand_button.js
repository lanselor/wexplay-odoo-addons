/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";

console.warn("WEXPLAY: expand button - Fixed visibility logic (2025-12-27)");

try {
    patch(ListController.prototype, {
        setup() {
            super.setup();

            this._wexBtn = null;
            this._wexSelfUpdate = false;
            this._wexObserver = null;
            this._wexInjectScheduled = false;

            // Limitar al modelo de reparaciones
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
                    if (this._wexSelfUpdate || this._wexInjectScheduled) return;
                    
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

        // VALIDACIÓN: ¿Es el elemento realmente visible para el usuario?
        // Esto ignora los grupos que los filtros de Odoo ocultan pero dejan en el DOM.
        _wexIsActuallyVisible(el) {
            if (!el) return false;
            // offsetHeight > 0 es la clave: si Odoo filtra la fila, su altura colapsa.
            const style = window.getComputedStyle(el);
            return style.display !== 'none' && el.offsetHeight > 0;
        },

        _wexHasFoldedGroups() {
            const headers = document.querySelectorAll("tr.o_group_has_content.o_group_header");
            return Array.from(headers).some(tr => {
                // Solo nos importan los grupos que el usuario está viendo actualmente
                if (!this._wexIsActuallyVisible(tr)) return false;

                const caret = tr.querySelector(".o_group_caret");
                return caret && (
                    caret.classList.contains("fa-caret-right") ||
                    caret.classList.contains("fa-chevron-right")
                );
            });
        },

        _wexUpdateButtonLabel() {
            if (!this._wexBtn) return;

            const hasFolded = this._wexHasFoldedGroups();
            this._wexSelfUpdate = true;

            this._wexBtn.innerHTML = hasFolded
                ? '<i class="fa fa-expand me-1"></i> Expandir'
                : '<i class="fa fa-compress me-1"></i> Plegar';

            // Pequeño delay para liberar el flag tras la mutación del DOM
            setTimeout(() => { this._wexSelfUpdate = false; }, 50);
        },

        injectWexButton() {
            const container =
                document.querySelector(".o_control_panel_main_buttons") ||
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

            btn.addEventListener("click", (ev) => {
                ev.preventDefault();
                this.wexHandleClick();
            });

            // Posicionamiento al lado de "Nuevo"
            const btnNuevo = container.querySelector("button.o_list_button_add") || 
                             container.querySelector("button.o_list_button_create");

            if (btnNuevo) {
                btnNuevo.insertAdjacentElement("afterend", btn);
            } else {
                container.appendChild(btn);
            }

            this._wexBtn = btn;
            this._wexUpdateButtonLabel();
        },

        async wexHandleClick() {
            // Decidimos la acción basándonos solo en lo que es visible AHORA
            const shouldExpand = this._wexHasFoldedGroups();
            const headers = document.querySelectorAll("tr.o_group_has_content.o_group_header");

            headers.forEach((tr) => {
                if (!this._wexIsActuallyVisible(tr)) return;

                const caret = tr.querySelector(".o_group_caret");
                if (!caret) return;

                const isFolded = caret.classList.contains("fa-caret-right") || 
                                 caret.classList.contains("fa-chevron-right");

                // LOGICA UNIDIRECCIONAL:
                // Si la orden es Expandir, solo clickamos los cerrados.
                // Si la orden es Plegar, solo clickamos los abiertos.
                if (shouldExpand && isFolded) {
                    tr.click();
                } else if (!shouldExpand && !isFolded) {
                    tr.click();
                }
            });

            // Odoo 18 necesita tiempo para procesar los clics y cambiar las clases CSS
            // Hacemos dos chequeos para asegurar que la etiqueta cambie sí o sí
            setTimeout(() => this._wexUpdateButtonLabel(), 100);
            setTimeout(() => this._wexUpdateButtonLabel(), 400);
        },
    });
} catch (e) {
    console.error("WEXPLAY: Fatal patch error", e);
}