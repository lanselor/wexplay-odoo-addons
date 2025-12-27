/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

console.log("WEX: cargado repair_order_expand_button.js (registrando wex_repair_list)");

const MAX_GROUPS = 200;

async function toggleGroup(controller, group) {
    const root = controller.model?.root;
    if (root?.toggleGroup) return root.toggleGroup(group);
    if (controller.model?.toggleGroup) return controller.model.toggleGroup(group);
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
        if (g?.isFolded) await toggleGroup(controller, g);
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
        if (!g?.isFolded) await toggleGroup(controller, g);
    }
}

class WexRepairListController extends ListController {
    setup() {
        super.setup(); // CRÍTICO: evita props/estado incompletos
    }

    async wexExpandGroups() {
        await expandAllGroups(this);
    }

    async wexCollapseGroups() {
        await collapseAllGroups(this);
    }
}

const WexRepairListView = {
    ...listView,
    Controller: WexRepairListController,
    buttonTemplate: "wexplay_repair.WexRepairListView.Buttons",
};

registry.category("views").add("wex_repair_list", WexRepairListView);
console.log("WEX: registrado view key = wex_repair_list");
