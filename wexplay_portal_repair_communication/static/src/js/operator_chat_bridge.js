/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

class WexPortalRepairOperatorChatBridge {
    constructor(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.store = services["mail.store"];
    }

    setup() {
        this.busService.subscribe("wex.portal_repair/operator_chat", async (payload) => {
            if (document.visibilityState !== "visible") {
                return;
            }
            const thread = await this.store.Thread.getOrFetch({
                model: "discuss.channel",
                id: payload.channel_id,
            });
            if (!thread) {
                console.warn(
                    "[WexPortalRepair] No se pudo obtener el canal SAT del store:",
                    payload.channel_id
                );
                return;
            }
            thread.open();
        });
    }
}

export const wexPortalRepairOperatorChatBridge = {
    dependencies: ["bus_service", "mail.store"],
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
