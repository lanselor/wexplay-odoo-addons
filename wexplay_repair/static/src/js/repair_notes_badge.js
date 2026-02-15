/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { onMounted, onPatched } from "@odoo/owl";

function htmlToText(html) {
    if (!html) return "";
    try {
        const doc = new DOMParser().parseFromString(String(html), "text/html");
        return (doc.body?.textContent || "").replace(/\u00A0/g, " ").trim(); // nbsp -> space
    } catch {
        // fallback ultra simple
        return String(html).replace(/<[^>]*>/g, "").replace(/\u00A0/g, " ").trim();
    }
}

function applyBadge(el, record) {
    if (!el || !record) return;

    // Limitar a repair.order para no afectar a otros formularios
    if (record.resModel !== "repair.order") return;

    const tab = el.querySelector(".o_notebook .nav-link[name='repair_notes']");
    if (!tab) return;

    // Campo real detectado en tu UI: internal_notes (Html)
    const raw = record.data?.internal_notes;
    const hasNotes = !!htmlToText(raw);

    tab.classList.toggle("wex_has_repair_notes", hasNotes);
}

patch(FormRenderer.prototype, "wexplay_repair.repair_notes_badge", {
    setup() {
        super.setup();

        onMounted(() => applyBadge(this.el, this.props.record));
        onPatched(() => applyBadge(this.el, this.props.record));
    },
});
