import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

console.log("WEXPLAY: repair_order_expand_button cargado");

// Guarda el original
const originalGetStaticActionMenuItems = ListController.prototype.getStaticActionMenuItems;

patch(ListController.prototype, {
   
     setup() {
        console.log("WEX: ListController expuesto", this.props?.resModel, this);
        if (this._super) this._super(...arguments);
        window._wex_last_list_controller = this;
        
    },
   
   
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
