/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ListView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

const MAX_GROUPS = 200;

async function toggleGroup(controller, group) {
    // Odoo puede exponer toggleGroup en distintos sitios según versión/estado
    const root = controller.model?.root;
    if (root?.toggleGroup) {
        return root.toggleGroup(group);
    }
    if (controller.model?.toggleGroup) {
        return controller.model.toggleGroup(group);
    }
    // Fallback: algunas implementaciones usan model.load/notify; aquí preferimos no romper nada
    console.warn("WEX: toggleGroup no disponible en este modelo/vista.");
}

async function expandAllGroups(controller) {
    const root = controller.model?.root;
    const groups = root?.groups || [];
    if (!groups.length) return;

    if (groups.length > MAX_GROUPS) {
        console.warn(`WEX: demasiados grupos (${groups.length}). Abortando expand.`);
        return;
    }

    for (const g of groups) {
        if (!g?.isFolded) continue;
        await toggleGroup(controller, g);
    }
}

async function collapseAllGroups(controller) {
    const root = controller.model?.root;
    const groups = root?.groups || [];
    if (!groups.length) return;

    if (groups.length > MAX_GROUPS) {
        console.warn(`WEX: demasiados grupos (${groups.length}). Abortando collapse.`);
        return;
    }

    for (const g of groups) {
        if (g?.isFolded) continue;
        await toggleGroup(controller, g);
    }
}

export class WexRepairListController extends ListController {
    async wexExpandGroups() {
        await expandAllGroups(this);
    }
    async wexCollapseGroups() {
        await collapseAllGroups(this);
    }
}

export const WexRepairListView = {
    ...ListView,
    Controller: WexRepairListController,
    buttonTemplate: "wexplay_repair.WexRepairListView.Buttons",
};

// Este string DEBE coincidir con js_class="wex_repair_list" en el <tree>
registry.category("views").add("wex_repair_list", WexRepairListView);
