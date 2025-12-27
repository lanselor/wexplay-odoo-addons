/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup();
        if (this.props.resModel !== "repair.order") return;

        onMounted(() => {
            // El observador vigila cambios en el DOM para re-inyectar el botón si Odoo lo borra
            this.wexObserver = new MutationObserver(() => this.injectWexButton());
            this.wexObserver.observe(document.body, { childList: true, subtree: true });
            
            // Primer intento inmediato
            this.injectWexButton();
        });

        onWillUnmount(() => {
            if (this.wexObserver) this.wexObserver.disconnect();
        });
    },

    injectWexButton() {
        // Buscamos el contenedor del botón "Nuevo" (o_cp_buttons)
        // Este contenedor suele estar presente siempre en la vista de lista
        const container = document.querySelector(".o_control_panel_main_buttons") || 
                          document.querySelector(".o_cp_buttons");

        if (!container || container.querySelector(".btn_wex_expand")) return;

        const btn = document.createElement("button");
        btn.type = "button";
        // btn-light o btn-secondary para que no compita visualmente con el botón verde de Nuevo
        btn.className = "btn btn-light btn_wex_expand ms-2 border"; 
        btn.innerHTML = '<i class="fa fa-expand me-1"></i> Expandir';
        
        btn.onclick = (ev) => {
            ev.preventDefault();
            this.wexplayExpandAll();
        };

        // Lo insertamos justo después del primer hijo (normalmente el botón Nuevo)
        if (container.firstChild) {
            container.insertBefore(btn, container.firstChild.nextSibling);
        } else {
            container.appendChild(btn);
        }
    },

    async wexplayExpandAll() {
        const root = this.model.root;
        if (root && root.groups) {
            // Quitamos el await de dentro del loop para que dispare todas las aperturas
            // esto lo hace mucho más rápido en Odoo 18
            const promises = root.groups
                .filter(g => g.isFolded)
                .map(group => this.model.toggleGroup(group));
            
            await Promise.all(promises);
        }
    }
});