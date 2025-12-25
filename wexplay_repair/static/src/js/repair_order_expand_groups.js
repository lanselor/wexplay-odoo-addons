/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        
        // Verificamos si es nuestro modelo
        if (this.props.resModel === "repair.order") {
            const root = this.model.root;
            
            // Sobrescribimos la función que carga los datos para inyectar la expansión
            const originalLoad = root.load.bind(root);
            root.load = async (params) => {
                if (root.groupBy && root.groupBy.length > 0) {
                    // 'expand: true' es la clave que Odoo usa internamente 
                    // para saber si debe mostrar los grupos abiertos
                    root.isFolded = false; 
                }
                return originalLoad(params);
            };
        }
    }
});