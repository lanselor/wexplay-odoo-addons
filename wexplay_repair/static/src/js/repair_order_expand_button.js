/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";

const MAX_GROUPS = 200;

function getGroups(root) {
    if (!root) return [];
    if (Array.isArray(root.groups)) return root.groups;
    return [];
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

    if (!groups.length) return; // no está agrupado
    if (groups.length > MAX_GROUPS) return; // guard-rail

    for (const g of groups) {
        if (isFolded(g)) {
            await toggleGroup(controller.model, g);
        }
    }
}

// Guardamos referencia al método original (si existe)
const _getActionMenuItems = ListController.prototype.getActionMenuItems;

patch(ListController.prototype, {
    getActionMenuItems(...args) {
        const res = _getActionMenuItems ? _getActionMenuItems.call(this, ...args) : { items: [] };

        // Solo en repair.order
        if (this.props?.resModel !== "repair.order") {
            return res;
        }

        // Estructura típica: { items: { other: [...] } } o { items: [...] } según versión
        // Normalizamos a array "other"
        if (Array.isArray(res?.items)) {
            res.items.push({
                description: "Desplegar grupos (Wexplay)",
                callback: () => expandAllGroups(this),
            });
            return res;
        }

        if (!res.items) res.items = {};
        if (!Array.isArray(res.items.other)) res.items.other = [];

        res.items.other.push({
            description: "Desplegar grupos (Wexplay)",
            callback: () => expandAllGroups(this),
        });

        return res;
    },
});
