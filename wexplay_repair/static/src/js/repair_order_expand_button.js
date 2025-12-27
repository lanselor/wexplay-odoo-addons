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
            const root = this.model?.root;
            const groups = root?.groups || [];

            // 1) Preferente: método en root (común en Odoo 17/18)
            if (typeof root?.toggleGroup === "function") {
                const promises = groups
                    .filter(g => g.isFolded)
                    .map(g => root.toggleGroup(g));
                await Promise.all(promises);
                return;
            }

            // 2) Fallback: algunos builds lo tienen en el controller
            if (typeof this?.toggleGroup === "function") {
                const promises = groups
                    .filter(g => g.isFolded)
                    .map(g => this.toggleGroup(g));
                await Promise.all(promises);
                return;
            }

            // 3) Diagnóstico (para ajustar a tu caso exacto)
            console.error("WEXPLAY: no encuentro toggleGroup en root/controller/model", {
                hasRoot: !!root,
                rootKeys: root ? Object.keys(root) : [],
                modelKeys: this.model ? Object.keys(this.model) : [],
                controllerKeys: Object.keys(this),
            });
        }



    });
} catch (e) {
    console.error("WEXPLAY: patch expand button failed", e);
}
