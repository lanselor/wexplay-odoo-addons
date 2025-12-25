/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useEffect } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        // En Odoo 18, usamos useEffect para monitorizar cuando los datos del modelo están listos
        useEffect(
            () => {
                if (this.props.resModel === "repair.order") {
                    const root = this.model.root;
                    // Verificamos que existan grupos y que no estén ya expandidos
                    if (root && root.groups && root.groups.length > 0) {
                        root.groups.forEach(group => {
                            if (group.isFolded) {
                                // En Odoo 18, toggleGroup es la forma segura de cambiar el estado
                                // Si no queremos disparar una recarga, cambiamos la propiedad directamente
                                group.isFolded = false;
                            }
                        });
                    }
                }
            },
            () => [this.model.root.groups] // Se dispara específicamente cuando cambian los grupos
        );
    },
});