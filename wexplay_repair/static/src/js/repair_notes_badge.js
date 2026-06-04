/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { onMounted, onPatched, useRef } from "@odoo/owl";

function htmlToText(html) {
    if (!html) return "";
    try {
        const doc = new DOMParser().parseFromString(String(html), "text/html");
        return (doc.body?.textContent || "").replace(/\u00A0/g, " ").trim();
    } catch {
        return String(html).replace(/<[^>]*>/g, "").replace(/\u00A0/g, " ").trim();
    }
}

function applyBadge(renderer) {
    try {
        const record = renderer?.props?.record;
        if (!record || record.resModel !== "repair.order") return;

        const el = renderer?.wexCompiledViewRoot?.el || renderer?.el;
        if (!el) return;

        const tab = el.querySelector(".o_notebook .nav-link[name='repair_notes']");
        if (!tab) return;

        const raw = record.data?.internal_notes;
        const hasNotes = !!htmlToText(raw);

        // Guard: evita bucles (solo tocar DOM si cambia)
        const next = hasNotes ? "1" : "0";
        if (tab.dataset.wexHasRepairNotes === next) return;

        tab.dataset.wexHasRepairNotes = next;
        tab.classList.toggle("wex_has_repair_notes", hasNotes);
    } catch (e) {
        // No romper el backend por un badge
        console.warn("WEX repair_notes_badge:", e);
    }
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        this.wexCompiledViewRoot = useRef("compiled_view_root");

        // Inicial y tras cada patch
        onMounted(() => applyBadge(this));
        onPatched(() => applyBadge(this));
    },
});
