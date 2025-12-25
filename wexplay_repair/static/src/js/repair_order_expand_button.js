/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

patch(ListController.prototype, {
    /**
     * @override
     */
    getActionMenuItems() {
        const res = super.getActionMenuItems(...arguments);
        
        // Solo aplicar en el modelo de reparaciones y si hay registros
        if (this.props.resModel === "repair.order" && res) {
            
            // Creamos la nueva acción
            const expandAction = {
                description: "Expandir todos los grupos",
                callback: () => this.wexplayExpandAll(),
                sequence: 100,
            };

            // En Odoo 18, res.other es donde viven las acciones adicionales
            if (!res.other) {
                res.other = [];
            }
            res.other.push(expandAction);
        }
        
        return res;
    },

    /**
     * Lógica de expansión
     */
    async wexplayExpandAll() {
        const root = this.model.root;
        if (root && root.groups) {
            // Filtramos los que están cerrados para no llamar al servidor innecesariamente
            const closedGroups = root.groups.filter(g => g.isFolded);
            
            for (const group of closedGroups) {
                // En Odoo 18, toggleGroup es la vía oficial
                await this.model.toggleGroup(group);
            }
        }
    }
});