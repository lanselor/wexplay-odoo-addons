/** @odoo-module **/

function update() {
    try {
        const tab = document.querySelector(".o_notebook .nav-link[name='repair_notes']");
        const pane = document.querySelector(".o_form_view .tab-pane[name='repair_notes'], .o_form_view .tab-pane[data-name='repair_notes']");
        if (!tab || !pane) return;

        let hasNotes = false;
        for (const el of pane.querySelectorAll("input, textarea")) {
            if ((el.value || "").trim()) { hasNotes = true; break; }
        }
        tab.classList.toggle("wex_has_repair_notes", hasNotes);
    } catch (e) {
        console.warn("repair_notes_badge:", e);
    }
}

window.addEventListener("input", update, true);
window.addEventListener("change", update, true);
update();
