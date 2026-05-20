/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

class WexPortalRepairOperatorChatBridge {
    constructor(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.store = services["mail.store"];
        this.multiTab = services.multi_tab;
    }

    setup() {
        this.busService.subscribe("wex.portal_repair/operator_chat", async (payload) => {
            if (!this.multiTab.isOnMainTab()) {
                return;
            }
            const thread = await this.store.Thread.getOrFetch({
                model: "discuss.channel",
                id: payload.channel_id,
            });
            thread?.open();
        });
    }
}

export const wexPortalRepairOperatorChatBridge = {
    dependencies: ["bus_service", "mail.store", "multi_tab"],
    start(env, services) {
        const bridge = reactive(new WexPortalRepairOperatorChatBridge(env, services));
        bridge.setup();
        return bridge;
    },
};

registry.category("services").add(
    "wex.portal_repair.operator_chat_bridge",
    wexPortalRepairOperatorChatBridge
);
