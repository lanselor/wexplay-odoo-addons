/** @odoo-module **/



import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

console.log("WEXPLAY: repair_order_expand_button cargado");

const MAX_GROUPS = 200;

async function expandAllGroups(controller) {
    const root = controller.model?.root;
    const groups = root?.groups || [];
    if (!groups.length) return;

    if (groups.length > MAX_GROUPS) {
        console.warn(`WEXPLAY: demasiados grupos (${groups.length}), no se expanden.`);
        return;
    }

    // En listas agrupadas, toggleGroup suele existir en el modelo
    if (!controller.model?.toggleGroup) {
        console.warn("WEXPLAY: model.toggleGroup no existe en esta vista.");
        return;
    }

    for (const g of groups) {
        const folded = g.isFolded ?? g.folded ?? false;
        if (folded) {
            await controller.model.toggleGroup(g);
        }
    }
}

patch(ListController.prototype, {
    /**
     * Odoo 18: getActionMenuItems() devuelve un objeto.
     * Aquí NO usamos this._super. Llamamos al original guardándolo antes.
     */
});

const originalGetActionMenuItems = ListController.prototype.getActionMenuItems;

patch(ListController.prototype, {
    getActionMenuItems() {
        const res = originalGetActionMenuItems.call(this, ...arguments);

        // >>> AQUÍ
        window._wex_last_list_controller = this;
        console.log("WEX: controller expuesto en window._wex_last_list_controller", this);
        // <<<
        
        // Solo en repair.order
        if (this.props?.resModel !== "repair.order") {
            return res;
        }

        // Normaliza estructura típica de action menu
        // (según versión puede ser res.items / res.other / etc.)
        if (!res) return res;

        // Intento de normalización defensiva
        if (res.items && Array.isArray(res.items.other)) {
            res.items.other.push({
                description: "Expandir grupos",
                callback: async () => {
                    await expandAllGroups(this);
                },
            });
            return res;
        }

        // Fallback: algunas builds usan res.other directamente
        if (Array.isArray(res.other)) {
            res.other.push({
                description: "Expandir grupos",
                callback: async () => {
                    await expandAllGroups(this);
                },
            });
            return res;
        }

        // Si no encontramos estructura conocida, lo dejamos sin romper nada
        console.warn("WEXPLAY: estructura de action menu no reconocida", res);
        return res;
    },
});
