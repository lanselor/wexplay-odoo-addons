/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onRendered } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup();
        if (this.props.resModel !== "repair.order") return;

        onRendered(() => {
            this.tryInjectButton();
        });
    },

    tryInjectButton() {
        // En Odoo 18, los botones pueden estar en varios sitios dependiendo del layout
        const selectors = [
            ".o_control_panel_main_buttons", // Botones principales (Nuevo, etc)
            ".o_cp_buttons",
            ".o_list_buttons",
            ".o_control_panel_actions"
        ];

        let container = null;
        for (const selector of selectors) {
            container = document.querySelector(selector);
            if (container) break;
        }

        if (!container) {
            // Si sigue siendo null, lo intentamos un poco más tarde (Odoo 18 async)
            if (!this.retryCount) this.retryCount = 0;
            if (this.retryCount < 10) {
                this.retryCount++;
                setTimeout(() => this.tryInjectButton(), 200);
            }
            return;
        }

        if (container.querySelector(".btn_wex_expand")) return;

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-secondary btn_wex_expand ms-2 border";
        btn.innerHTML = '<i class="fa fa-expand me-1"></i> Expandir';
        
        btn.onclick = async (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            await this.wexplayExpandAll();
        };

        container.appendChild(btn);
        this.retryCount = 0; // Reset si tuvo éxito
    },

    async wexplayExpandAll() {
        const root = this.model.root;
        if (root && root.groups) {
            for (const group of root.groups) {
                if (group.isFolded) {
                    await this.model.toggleGroup(group);
                }
            }
        }
    }
});