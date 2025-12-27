import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

// Guarda originales ANTES del patch
const originalSetup = ControlPanel.prototype.setup;
const originalGetStaticActionMenuItems = ListController.prototype.getStaticActionMenuItems;


patch(ListController.prototype, {

    setup() {
        originalSetup.call(this, ...arguments);
        window._wex_last_list_controller = this;
        window.wexExpandGroups = () => this.wexExpandGroups();
        window.wexCollapseGroups = () => this.wexCollapseGroups();
        window._wex_cp = this;

        // Log compacto para no inundar
        console.log("WEX CP keys:", Object.keys(this.props || {}));
        console.log("WEX CP props:", this.props);
    },

    // Handlers para los botones del Control Panel (siempre visibles)
    async wexExpandGroups() {
        if (this.props?.resModel !== "repair.order") return;
        await expandAllGroups(this);
    },

    async wexCollapseGroups() {
        if (this.props?.resModel !== "repair.order") return;
        await collapseAllGroups(this);
    },

    // Mantengo esto por compatibilidad/si aún quieres la opción en el menú "Acciones" (bulk)
    // Puedes eliminar este método si ya no lo necesitas.
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
