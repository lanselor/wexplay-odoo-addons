/** @odoo-module **/

(function () {
    "use strict";

    function getTab() {
        return document.querySelector(".o_notebook .nav-link[name='repair_notes']");
    }

    function getPaneFromTab(tab) {
        if (!tab) return null;

        // Odoo normalmente pone aria-controls con el id del panel
        const paneId = tab.getAttribute("aria-controls");
        if (paneId) {
            return document.getElementById(paneId);
        }

        // Fallback: si usa href="#id"
        const href = tab.getAttribute("href") || "";
        if (href.startsWith("#")) {
            return document.getElementById(href.slice(1));
        }

        return null;
    }

    function hasHtmlNotes(pane) {
        if (!pane) return false;

        // HTML editor -> contenteditable (cuando el tab ya se ha renderizado)
        const editables = pane.querySelectorAll("[contenteditable='true']");
        for (const el of editables) {
            const txt = (el.textContent || "").replace(/\u00A0/g, " ").trim();
            if (txt) return true;
        }

        // Fallback: input/textarea ocultos
        for (const el of pane.querySelectorAll("textarea, input")) {
            const v = (el.value || "").trim();
            if (v) return true;
        }

        return false;
    }

    function update() {
        try {
            const tab = getTab();
            if (!tab) return;

            const pane = getPaneFromTab(tab);
            if (!pane) return;

            const hasNotes = hasHtmlNotes(pane);
            tab.classList.toggle("wex_has_repair_notes", hasNotes);
        } catch (e) {
            console.warn("repair_notes_badge:", e);
        }
    }

    function boot() {
        window.addEventListener("input", update, true);
        window.addEventListener("change", update, true);

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
