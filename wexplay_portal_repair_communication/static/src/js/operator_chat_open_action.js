/** @odoo-module **/

import { registry } from "@web/core/registry";
import { openPortalRepairOperatorChat } from "./operator_chat_open";

registry.category("actions").add(
    "wex_portal_repair_communication.open_operator_chat",
    async (env, action) => {
        const params = action?.params || {};
        const opened = await openPortalRepairOperatorChat(env, params);
        if (opened) {
            return;
        }

        const conversationId = params.conversation_id;
        if (conversationId) {
            await env.services.action.doAction({
                type: "ir.actions.act_window",
                name: "Conversacion SAT",
                res_model: "wex.portal.repair.conversation",
                res_id: conversationId,
                view_mode: "form",
                target: "current",
            });
            return;
        }

        env.services.notification.add(
            "No se pudo abrir el chat SAT en este momento.",
            { type: "warning" }
        );
    }
);
