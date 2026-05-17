/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { onMounted, onPatched } from "@odoo/owl";

function applyNotebookFocus(renderer) {
    try {
        const record = renderer?.props?.record;
        if (!record || record.resModel !== "wex.teardown.batch") {
            return;
        }
        const focus = record.data?.workflow_focus;
        if (!focus) {
            return;
        }
        const el = renderer?.el || document.querySelector(".o_form_view");
        if (!el) {
            return;
        }
        const tab = el.querySelector(`.o_notebook .nav-link[name='${focus}']`);
        if (!tab) {
            return;
        }
        const isActive = tab.classList.contains("active") || tab.getAttribute("aria-selected") === "true";
        if (!isActive) {
            tab.click();
        }
    } catch (error) {
        console.warn("WEX teardown notebook focus:", error);
    }
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup();
        onMounted(() => applyNotebookFocus(this));
        onPatched(() => applyNotebookFocus(this));
    },
});
