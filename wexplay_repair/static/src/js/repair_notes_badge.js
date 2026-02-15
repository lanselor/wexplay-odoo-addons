/** @odoo-module **/

(function () {
    "use strict";

    function getPane() {
        return (
            document.querySelector(".o_form_view .tab-pane[name='repair_notes']") ||
            document.querySelector(".o_form_view .tab-pane[data-name='repair_notes']")
        );
    }

    function hasHtmlNotes(pane) {
        // 1) Cualquier contenteditable dentro del pane (Odoo HTML editor)
        const editables = pane.querySelectorAll("[contenteditable='true']");
        for (const el of editables) {
            const txt = (el.textContent || "").replace(/\u00A0/g, " ").trim(); // nbsp -> space
            if (txt) return true;
        }

        // 2) Fallback: algunos editores guardan en un textarea/input oculto
        for (const el of pane.querySelectorAll("textarea, input")) {
            const v = (el.value || "").trim();
            if (v) return true;
        }

        return false;
    }

    function update() {
        try {
            const tab = document.querySelector(".o_notebook .nav-link[name='repair_notes']");
            if (!tab) return;

            const pane = getPane();
            if (!pane) return;

            const hasNotes = hasHtmlNotes(pane);
            tab.classList.toggle("wex_has_repair_notes", hasNotes);
        } catch (e) {
            console.warn("repair_notes_badge:", e);
        }
    }

    function boot() {
        // input/change cubre muchas interacciones del editor
        window.addEventListener("input", update, true);
        window.addEventListener("change", update, true);

        // observer para re-render OWL / cambios de tab
        const obs = new MutationObserver(update);
        obs.observe(document.documentElement, { childList: true, subtree: true });

        update();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }
})();
