/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useEffect } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        useEffect(
            () => {
                if (this.props.resModel === "repair.order") {
                    const root = this.model.root;
                    // En Odoo 18, los grupos están en root.groups
                    if (root && root.groups) {
                        for (const group of root.groups) {
                            // Verificamos si el grupo está plegado
                            if (group.isFolded) {
                                // En Odoo 18 el método está en el modelo, no en el root
                                // Pasamos el datapoint del grupo
                                this.model.toggleGroup(group);
                            }
                        }
                    }
                }
            },
            () => [this.model.root?.groups]
        );
    },
});