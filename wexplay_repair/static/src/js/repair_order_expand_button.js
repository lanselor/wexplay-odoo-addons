/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onRendered } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup();

        // Solo actuar si es nuestro modelo de reparaciones
        if (this.props.resModel !== "repair.order") {
            return;
        }

        console.log("WEXPLAY: ListController preparado para Repair Order");

        // Usamos onRendered para asegurar que si Odoo redibuja la barra, 
        // nosotros volvemos a verificar si el botón debe estar ahí.
        onRendered(() => {
            this.injectWexplayButton();
        });
    },

    injectWexplayButton() {
        // Buscamos el contenedor de botones oficial de Odoo 18
        // El selector .o_cp_buttons suele estar dentro del .o_control_panel
        const container = document.querySelector(".o_control_panel .o_cp_buttons") || 
                          document.querySelector(".o_list_buttons");

        if (!container) return;

        // Evitar duplicados
        if (container.querySelector(".btn_wex_expand")) return;

        // Crear botón con clases nativas de Odoo 18
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-secondary btn_wex_expand ms-2"; // ms-2 para dar margen
        btn.innerHTML = '<i class="fa fa-expand me-1"></i> Expandir Grupos';
        
        btn.onclick = async () => {
            console.log("WEXPLAY: Ejecutando expansión...");
            await this.wexplayExpandAll();
        };

        container.appendChild(btn);
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