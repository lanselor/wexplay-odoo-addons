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

(function boot() {
    const handler = () => update();

    document.addEventListener("input", handler, true);
    document.addEventListener("change", handler, true);

    // Observa SIEMPRE un Node válido
    const target = document.documentElement; // siempre existe y es Node
    const obs = new MutationObserver(() => update());
    obs.observe(target, { childList: true, subtree: true });

    update();
})();
