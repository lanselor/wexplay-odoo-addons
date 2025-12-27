/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";

try {
    patch(ListController.prototype, {
        setup() {
            super.setup();
            if (this.props?.resModel !== "repair.order") return;

            this._wexObserver = null;
            this._wexUpdateTimer = null;

            onMounted(() => {
                // Inyectar inmediatamente
                this.wexSyncUI();

                // Observar el Control Panel con un throttle más robusto
                const cp = document.querySelector(".o_control_panel");
                if (cp) {
                    this._wexObserver = new MutationObserver(() => {
                        // Usamos un pequeño debounce para esperar a que Odoo termine de pintar los filtros
                        clearTimeout(this._wexUpdateTimer);
                        this._wexUpdateTimer = setTimeout(() => this.wexSyncUI(), 100);
                    });
                    this._wexObserver.observe(cp, { childList: true, subtree: true });
                }
            });

            onWillUnmount(() => {
                this._wexObserver?.disconnect();
                clearTimeout(this._wexUpdateTimer);
            });
        },

        // Comprobación de visibilidad infalible en Odoo 18
        wexIsVisible(el) {
            return !!(el && el.offsetWidth > 0 && el.offsetHeight > 0);
        },

        wexHasFolded() {
            const headers = document.querySelectorAll("tr.o_group_header.o_group_has_content");
            return Array.from(headers).some(tr => {
                if (!this.wexIsVisible(tr)) return false;
                const caret = tr.querySelector(".o_group_caret");
                return caret && (caret.classList.contains("fa-caret-right") || caret.classList.contains("fa-chevron-right"));
            });
        },

        wexSyncUI() {
            const container = document.querySelector(".o_control_panel_main_buttons") || 
                              document.querySelector(".o_cp_buttons");
            if (!container) return;

            let btn = container.querySelector("[data-wex='expand']");
            
            // Si no existe, lo creamos de cero
            if (!btn) {
                btn = document.createElement("button");
                btn.type = "button";
                btn.className = "btn btn-outline-primary btn-sm ms-2 border";
                btn.setAttribute("data-wex", "expand");
                btn.onclick = (ev) => {
                    ev.preventDefault();
                    this.wexHandleAction();
                };
                
                // Posicionamiento detrás del botón Nuevo
                const btnAdd = container.querySelector(".o_list_button_add, .o_list_button_create");
                if (btnAdd) btnAdd.insertAdjacentElement("afterend", btn);
                else container.appendChild(btn);
            }

            // Actualizamos el texto SIEMPRE basándonos en el DOM actual
            const hasFolded = this.wexHasFolded();
            btn.innerHTML = hasFolded
                ? '<i class="fa fa-expand me-1"></i> Expandir'
                : '<i class="fa fa-compress me-1"></i> Plegar';
        },

        async wexHandleAction() {
            const shouldExpand = this.wexHasFolded();
            const headers = document.querySelectorAll("tr.o_group_header.o_group_has_content");
            
            // Ejecutamos los clics
            headers.forEach(tr => {
                if (!this.wexIsVisible(tr)) return;
                const caret = tr.querySelector(".o_group_caret");
                if (!caret) return;
                const isFolded = caret.classList.contains("fa-caret-right") || caret.classList.contains("fa-chevron-right");
                
                if (shouldExpand === isFolded) {
                    tr.click();
                }
            });

            // Forzamos sincronización de la etiqueta tras el cambio
            //setTimeout(() => this.wexSyncUI(), 200);
            setTimeout(() => this.wexSyncUI(), 50); // Segundo chequeo por si el servidor tarda
        }
    });
} catch (e) {
    console.error("WEXPLAY Error:", e);
}