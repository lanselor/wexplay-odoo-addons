/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { core } from "@web/core/utils/core";

// No usamos una IIFE manual, Odoo ya lo maneja con @odoo-module
function update() {
    const tab = document.querySelector(".o_notebook .nav-link[name='repair_notes']");
    if (!tab) return;

    const pane = document.querySelector(".o_form_view .tab-pane[name='repair_notes'], .o_form_view .tab-pane[data-name='repair_notes']");
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
}

// En lugar de MutationObserver global, usamos los eventos del bus de Odoo
// o un intervalo controlado si es necesario, pero lo más limpio es el evento de renderizado.
export const repairNotesBadge = {
    start() {
        browser.addEventListener("input", (ev) => {
            if (ev.target.closest(".tab-pane[name='repair_notes']")) {
                update();
            }
        });
        
        // El truco para Odoo: MutationObserver solo al cuerpo de la vista
        const observer = new MutationObserver(update);
        const config = { childList: true, subtree: true };
        
        // Esperamos a que el cuerpo de la web esté listo
        const mainElement = document.body; 
        if (mainElement) {
            observer.observe(mainElement, config);
        }
    }
};

// Iniciar cuando el DOM esté listo mediante el sistema de Odoo
browser.setTimeout(() => {
    repairNotesBadge.start();
}, 1000);