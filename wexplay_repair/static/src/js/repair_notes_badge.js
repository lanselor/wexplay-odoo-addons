/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { onMounted, onPatched } from "@odoo/owl";

console.warn("WEX repair_notes_badge asset LOADED");

function htmlToText(html) {
    if (!html) return "";
    const doc = new DOMParser().parseFromString(String(html), "text/html");
    return (doc.body?.textContent || "").replace(/\u00A0/g, " ").trim();
}

function applyBadge(renderer) {
    try {
        const record = renderer?.props?.record;
        const el = renderer?.el;

        console.warn("WEX applyBadge() called", {
            hasEl: !!el,
            model: record?.resModel,
            hasRecord: !!record,
        });

        if (!record || !el) return;
        if (record.resModel !== "repair.order") return;

        const tab = el.querySelector(".o_notebook .nav-link[name='repair_notes']");
        console.warn("WEX tab found?", !!tab);

        if (!tab) return;

        const raw = record.data?.internal_notes;
        const hasNotes = !!htmlToText(raw);

        console.warn("WEX internal_notes length", (raw || "").length, "hasNotes", hasNotes);

        tab.classList.toggle("wex_has_repair_notes", hasNotes);
    } catch (e) {
        console.warn("WEX applyBadge error:", e);
    }
}

patch(FormRenderer.prototype, "wexplay_repair.repair_notes_badge", {
    setup() {
        super.setup();
        onMounted(() => applyBadge(this));
        onPatched(() => applyBadge(this));
    },
});
