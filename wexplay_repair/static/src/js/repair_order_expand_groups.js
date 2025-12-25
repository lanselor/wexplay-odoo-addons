/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useEffect } from "@odoo/owl";

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        useEffect(
            () => {
                const root = this.model.root;
                if (this.props.resModel === "repair.order" && root && root.groups) {
                    // Buscamos grupos que estén plegados
                    const groupsToExpand = root.groups.filter(g => g.isFolded);
                    
                    if (groupsToExpand.length > 0) {
                        // Usamos la función nativa para expandirlos. 
                        // En Odoo 18 esto es asíncrono y seguro.
                        for (const group of groupsToExpand) {
                            // toggleGroup acepta el grupo o el id del grupo
                            root.toggleGroup(group);
                        }
                    }
                }
            },
            () => [this.model.root.groups]
        );
    },
});