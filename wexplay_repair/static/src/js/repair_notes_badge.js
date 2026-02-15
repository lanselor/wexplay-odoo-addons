/** @odoo-module **/

(function () {
    "use strict";

    function update() {
        try {
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
        } catch (e) {
            console.warn("repair_notes_badge update error:", e);
        }
    }

    function boot() {
        try {
            window.addEventListener("input", update, true);
            window.addEventListener("change", update, true);

            const target = document.documentElement; // siempre Node
            const obs = new MutationObserver(() => update());
            obs.observe(target, { childList: true, subtree: true });

            update();
        } catch (e) {
            console.warn("repair_notes_badge boot error:", e);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
