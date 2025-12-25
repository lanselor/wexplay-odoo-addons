import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Guarda originales ANTES del patch
const originalSetup = ListController.prototype.setup;
const originalGetStaticActionMenuItems = ListController.prototype.getStaticActionMenuItems;

patch(ListController.prototype, {
    setup() {
        // IMPRESCINDIBLE: llamar al setup original
        originalSetup.call(this, ...arguments);

        // Debug
        window._wex_last_list_controller = this;
        console.log("WEX: ListController expuesto", this.props?.resModel, this);
    },

    getStaticActionMenuItems() {
        const items = originalGetStaticActionMenuItems.call(this, ...arguments) || {};

        if (this.props?.resModel !== "repair.order") {
            return items;
        }

        if (!items.wex_expand_groups) {
            items.wex_expand_groups = {
                description: "Expandir grupos",
                callback: async () => {
                    await expandAllGroups(this);
                },
            };
        }

        if (!items.wex_collapse_groups) {
            items.wex_collapse_groups = {
                description: "Colapsar grupos",
                callback: async () => {
                    await collapseAllGroups(this);
                },
            };
        }

        return items;
    },
});
