/** @odoo-module **/

function update() {
    const tab = document.querySelector(".o_notebook .nav-link[name='repair_notes']");
    if (!tab) return;

    const pane =
        document.querySelector(".o_form_view .tab-pane[name='repair_notes']") ||
        document.querySelector(".o_form_view .tab-pane[data-name='repair_notes']");
    if (!pane) return;

    let hasNotes = false;
    for (const el of pane.querySelectorAll("input, textarea")) {
        if ((el.value || "").trim()) {
            hasNotes = true;
            break;
        }
    }
    tab.classList.toggle("wex_has_repair_notes", hasNotes);
}

document.addEventListener("input", (ev) => {
    if (ev.target && ev.target.closest(".o_form_view")) update();
});
document.addEventListener("change", (ev) => {
    if (ev.target && ev.target.closest(".o_form_view")) update();
});

new MutationObserver(update).observe(document.body, { childList: true, subtree: true });
update();
