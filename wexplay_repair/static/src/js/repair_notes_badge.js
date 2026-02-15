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

            const fields = pane.querySelectorAll("input, textarea");
            for (const el of fields) {
                if ((el.value || "").trim()) {
                    hasNotes = true;
                    break;
                }
            }

            tab.classList.toggle("wex_has_repair_notes", hasNotes);

        } catch (error) {
            console.warn("repair_notes_badge update error:", error);
        }
    }

    function boot() {
        try {
            document.addEventListener("input", update, true);
            document.addEventListener("change", update, true);

            const target = document.documentElement;
            if (target instanceof Node) {
                const observer = new MutationObserver(() => {
                    try {
                        update();
                    } catch (e) {
                        console.warn("MutationObserver error:", e);
                    }
                });

                observer.observe(target, {
                    childList: true,
                    subtree: true,
                });
            }

            update();

        } catch (error) {
            console.warn("repair_notes_badge boot error:", error);
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot, { once: true });
    } else {
        boot();
    }

})();
