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

        // FIX: en algunos ciclos OWL renderer.el aún no existe
        // Fallback al formulario visible
        const el = renderer?.el || document.querySelector(".o_form_view");

        console.warn("WEX applyBadge() called", {
            hasEl: !!el,
            model: record?.resModel,
            hasRecord: !!record,
        });

        if (!record || !el) return;
        if (record.resModel !== "repair.order") return;

        const tab = el.querySelector(".o_notebook .nav-link[name='repair_notes']");
        console.warn("WEX tab found?", !!tab);

        console.warn("WEX applyBadge debug", {
            model: record?.resModel,
            hasEl: !!el,
            tabFound: !!tab,
            internalNotesType: typeof record?.data?.internal_notes,
            internalNotesLen: (record?.data?.internal_notes || "").length,
        });

        if (!tab) return;

        const raw = record.data?.internal_notes;
        const hasNotes = !!htmlToText(raw);

        console.warn("WEX internal_notes length", (raw || "").length, "hasNotes", hasNotes);

        const prev = tab.dataset.wexHasRepairNotes;
        const next = hasNotes ? "1" : "0";
        if (prev === next) return;           // no tocar DOM si no cambia
        tab.dataset.wexHasRepairNotes = next;
        tab.classList.toggle("wex_has_repair_notes", hasNotes);
        
    } catch (e) {
        console.warn("WEX applyBadge error:", e);
    }
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        onMounted(() => applyBadge(this));
        onPatched(() => applyBadge(this));
    },
});
