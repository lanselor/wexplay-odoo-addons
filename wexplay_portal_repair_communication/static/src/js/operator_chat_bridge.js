/** @odoo-module **/

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

const STORAGE_EVENT_KEY = "wex_portal_repair_operator_chat";

class WexPortalRepairOperatorChatBridge {
    constructor(env, services) {
        this.env = env;
        this.busService = services.bus_service;
        this.store = services["mail.store"];
        this._lastProcessedEventKey = null;
    }

    setup() {
        this.busService.subscribe(
            "wex.portal_repair/operator_chat",
            async (payload) => await this.handleOperatorChatEvent(payload, { relayToOtherTabs: true })
        );
        window.addEventListener("storage", async (event) => {
            if (event.key !== STORAGE_EVENT_KEY || !event.newValue) {
                return;
            }
            try {
                const payload = JSON.parse(event.newValue);
                await this.handleOperatorChatEvent(payload);
            } catch (error) {
                console.warn("[WexPortalRepair] No se pudo procesar el relay multi-tab:", error);
            }
        });
    }

    async handleOperatorChatEvent(payload, options = {}) {
        const { relayToOtherTabs = false } = options;
        if (!payload?.channel_id) {
            return;
        }
        const normalizedPayload = {
            ...payload,
            ts: payload.ts || Date.now(),
        };
        const eventKey = `${normalizedPayload.channel_id}:${normalizedPayload.ts}`;
        if (this._lastProcessedEventKey === eventKey) {
            return;
        }
        if (relayToOtherTabs) {
            this.relayOperatorChatToOtherTabs(normalizedPayload);
        }
        if (document.visibilityState !== "visible") {
            return;
        }
        this._lastProcessedEventKey = eventKey;
        await this.openOperatorThread(normalizedPayload.channel_id);
    }

    relayOperatorChatToOtherTabs(payload) {
        try {
            window.localStorage.setItem(
                STORAGE_EVENT_KEY,
                JSON.stringify({
                    channel_id: payload.channel_id,
                    repair_id: payload.repair_id || false,
                    conversation_id: payload.conversation_id || false,
                    ts: Date.now(),
                })
            );
        } catch (error) {
            console.warn("[WexPortalRepair] No se pudo reenviar el evento multi-tab:", error);
        }
    }

    async openOperatorThread(channelId) {
        if (!channelId) {
            return;
        }
        const thread = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: channelId,
        });
        if (!thread) {
            console.warn("[WexPortalRepair] No se pudo obtener el canal SAT del store:", channelId);
            return;
        }
        thread.open();
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
