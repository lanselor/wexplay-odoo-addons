/** @odoo-module **/
console.log("WEXPLAY: repair_order_expand_button cargado");

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

const MAX_GROUPS = 200;

function getGroups(root) {
    return root?.groups || [];
}

function isFolded(g) {
    if (typeof g?.isFolded === "boolean") return g.isFolded;
    if (typeof g?.folded === "boolean") return g.folded;
    if (typeof g?.isOpen === "boolean") return !g.isOpen;
    if (typeof g?.open === "boolean") return !g.open;
    return false;
}

async function toggleGroup(model, group) {
    if (model?.toggleGroup) return model.toggleGroup(group);
    if (model?.root?.toggleGroup) return model.root.toggleGroup(group);
    return null;
}

async function expandAllGroups(controller) {
    const root = controller.model?.root;
    const groups = getGroups(root);

    if (!groups.length) return;
    if (groups.length > MAX_GROUPS) return;

    for (const g of groups) {
        if (isFolded(g)) {
            await toggleGroup(controller.model, g);
        }
    }
}

patch(ListController.prototype, {
    getActionMenuItems() {
        const res = this._super(...arguments);

        // Solo en repair.order
        if (this.props?.resModel !== "repair.order") {
            return res;
        }

        // Normaliza estructura
        if (!res?.items) res.items = {};
        if (!Array.isArray(res.items.other)) res.items.other = [];

        res.items.other.push({
            description: "Desplegar grupos (Wexplay)",
            callback: () => expandAllGroups(this),
        });

        return res;
    },
});
