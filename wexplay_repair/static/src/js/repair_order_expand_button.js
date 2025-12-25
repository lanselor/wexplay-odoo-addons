/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";
import { xml } from "@odoo/owl";

/**
 * Wexplay - Botón "Desplegar grupos" en listas agrupadas (repair.order)
 *
 * Objetivo:
 * - Añadir un botón en la barra de acciones de la vista lista (solo en repair.order).
 * - Al pulsarlo, intentar desplegar todos los grupos plegados del groupBy actual.
 *
 * Nota:
 * - Los "internals" de grupos cambian entre versiones. Este código es defensivo.
 * - Si hay muchos grupos, esto puede ser pesado; se aplica un límite.
 */

const TEMPLATE_NAME = "wexplay_repair.RepairOrderExpandButton";
const MAX_GROUPS = 200;

/** Devuelve array de grupos del root (según estructura disponible) */
function getGroups(root) {
    if (!root) return [];
    // En listas agrupadas suele existir root.groups
    if (Array.isArray(root.groups)) return root.groups;
    // Fallbacks por si Odoo cambia internals
    if (Array.isArray(root.groupBy)) return root.groupBy;
    return [];
}

/** Heurística para detectar si un grupo está plegado */
function isGroupFolded(g) {
    // Distintas versiones usan flags distintos
    if (typeof g?.isFolded === "boolean") return g.isFolded;
    if (typeof g?.folded === "boolean") return g.folded;
    if (typeof g?.isOpen === "boolean") return !g.isOpen;
    if (typeof g?.open === "boolean") return !g.open;
    // Si no sabemos, no tocamos
    return false;
}

/** Intenta desplegar un grupo usando APIs conocidas */
async function toggleGroup(model, group) {
    // API habitual: model.toggleGroup(group)
    if (model?.toggleGroup) {
        return model.toggleGroup(group);
    }
    // A veces está en root
    if (model?.root?.toggleGroup) {
        return model.root.toggleGroup(group);
    }
    // No hay API pública conocida
    return null;
}

patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);

        // Inyectamos el botón en el template del controlador de lista.
        // Odoo 18 permite extender `buttonsTemplate` (si existe) o añadir un slot.
        // Aquí usamos la aproximación estándar: añadir un template extra al area de botones.
        onMounted(() => {
            // Evita tocar otras vistas/modelos
            if (this.props?.resModel !== "repair.order") return;

            // Si el controlador no expone contenedor de botones, no hacemos nada.
            // En Odoo web, suele existir this.el y un nodo con clase .o_list_buttons
            const buttons = this.el?.querySelector(".o_list_buttons");
            if (!buttons) return;

            // Evitar duplicado si el controlador se remonta
            if (buttons.querySelector(".o_list_button_expand_groups")) return;

            // Render mínimo del botón (sin depender de qweb runtime).
            // Usamos el template XML cargado como assets: TEMPLATE_NAME.
            // Si no está disponible, fallback a botón simple.
            let btnEl = null;

            try {
                // `this.env.qweb` existe en Odoo webclient
                const html = this.env.qweb.render(TEMPLATE_NAME, {});
                const tmp = document.createElement("div");
                tmp.innerHTML = html.trim();
                btnEl = tmp.firstElementChild;
            } catch (e) {
                // Fallback
                btnEl = document.createElement("button");
                btnEl.type = "button";
                btnEl.className = "btn btn-secondary o_list_button_expand_groups";
                btnEl.title = "Desplegar todos los grupos";
                btnEl.textContent = "Desplegar grupos";
            }

            if (!btnEl) return;

            // Click handler
            btnEl.addEventListener("click", async () => {
                try {
                    const root = this.model?.root;
                    const groups = getGroups(root);

                    if (!groups.length) {
                        // No está agrupado: nada que desplegar
                        return;
                    }
                    if (groups.length > MAX_GROUPS) {
                        // Guard-rail: no desplegar si es enorme
                        return;
                    }

                    // Desplegar solo los plegados
                    for (const g of groups) {
                        if (isGroupFolded(g)) {
                            // No bloqueamos UI con awaits largos: encolamos microtareas
                            // pero mantenemos secuencia ligera
                            await toggleGroup(this.model, g);
                        }
                    }
                } catch (err) {
                    // No romper UI
                    // console.error(err);
                }
            });

            // Insertar el botón (al final de los botones de lista)
            buttons.appendChild(btnEl);
        });
    },
});
