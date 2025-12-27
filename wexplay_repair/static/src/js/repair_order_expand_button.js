import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Guarda originales ANTES del patch
const originalListSetup = ListController.prototype.setup;
const originalGetStaticActionMenuItems = ListController.prototype.getStaticActionMenuItems;

patch(ListController.prototype, {
    setup() {
            originalListSetup.call(this, ...arguments);

            if (this.props?.resModel === "repair.order") {
                window._wex_last_list_controller = this;
                window.wexExpandGroups = () => this.wexExpandGroups();
                window.wexCollapseGroups = () => this.wexCollapseGroups();
            } else {
                if (window._wex_last_list_controller === this) {
                    delete window._wex_last_list_controller;
                    delete window.wexExpandGroups;
                    delete window.wexCollapseGroups;
                }
            }

            console.log("WEX ListController resModel:", this.props?.resModel);
        },

    async wexExpandGroups() {
        if (this.props?.resModel !== "repair.order") return;
        await expandAllGroups(this);
    },

    async wexCollapseGroups() {
        if (this.props?.resModel !== "repair.order") return;
        await collapseAllGroups(this);
    },

    getStaticActionMenuItems() {
        const items = originalGetStaticActionMenuItems.call(this, ...arguments) || {};

        if (this.props?.resModel !== "repair.order") return items;

        items.wex_expand_groups ||= {
            description: "Expandir grupos",
            callback: async () => expandAllGroups(this),
        };

        items.wex_collapse_groups ||= {
            description: "Colapsar grupos",
            callback: async () => collapseAllGroups(this),
        };

        return items;
    },
});
