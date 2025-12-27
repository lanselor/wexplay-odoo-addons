/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

const originalGetStatic = ListController.prototype.getStaticActionMenuItems;

patch(ListController.prototype, {
    getStaticActionMenuItems() {
        const items = (originalGetStatic && originalGetStatic.call(this, ...arguments)) || {};

        // Filtro por modelo
        if (this.props?.resModel !== "repair.order") return items;

        // Evitar duplicados
        if (!items.wex_expand_all) {
            items.wex_expand_all = {
                description: "Expandir todos los grupos",
                callback: async () => {
                    await this.wexplayExpandAll();
                },
            };
        }

        return items;
    },

    async wexplayExpandAll() {
        const root = this.model?.root;
        const groups = root?.groups || [];
        for (const g of groups) {
            if (g?.isFolded) {
                if (root?.toggleGroup) await root.toggleGroup(g);
                else if (this.model?.toggleGroup) await this.model.toggleGroup(g);
            }
        }
    },
});
