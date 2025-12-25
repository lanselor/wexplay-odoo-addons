import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Guarda el original
const originalGetStaticActionMenuItems = ListController.prototype.getStaticActionMenuItems;

patch(ListController.prototype, {
    getStaticActionMenuItems() {
        const items = originalGetStaticActionMenuItems.call(this, ...arguments) || {};

        // Solo en repair.order
        if (this.props?.resModel !== "repair.order") {
            return items;
        }

        // Evita duplicados
        if (!items.wex_expand_groups) {
            items.wex_expand_groups = {
                description: "Expandir grupos",
                callback: async () => {
                    await expandAllGroups(this);   // tu función
                },
            };
        }

        // (Opcional) también “Colapsar”
        if (!items.wex_collapse_groups) {
            items.wex_collapse_groups = {
                description: "Colapsar grupos",
                callback: async () => {
                    await collapseAllGroups(this); // si la tienes
                },
            };
        }

        return items;
    },
});
