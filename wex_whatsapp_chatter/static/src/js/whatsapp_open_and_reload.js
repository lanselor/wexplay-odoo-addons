/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

registry.category("actions").add("wex_whatsapp_chatter.open_whatsapp_and_reload", async (env, action) => {
    const url = action?.params?.url;
    if (!url) {
        return;
    }

    // Abrimos WhatsApp en nueva pestaña
    browser.open(url, "_blank");

    // Cerramos el wizard/modal actual
    await env.services.action.doAction({
        type: "ir.actions.act_window_close",
    });

    // Recargamos la vista actual para que el chatter muestre la nota sin refresco manual
    await env.services.action.doAction({
        type: "ir.actions.client",
        tag: "reload",
    });
});