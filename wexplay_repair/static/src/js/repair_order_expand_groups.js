/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted, onWillUpdateProps } from "@odoo/owl";

const _setup = ListController.prototype.setup;

function collectGroups(node) {
    const out = [];
    const seen = new Set();

    const walk = (n) => {
        if (!n) return;

        // Caso típico: n.groups
        if (Array.isArray(n.groups)) {
            for (const g of n.groups) {
                if (g && !seen.has(g)) {
                    seen.add(g);
                    out.push(g);
                    walk(g); // por si hay subgrupos
                }
            }
        }

        // Algunas variantes: n.data contiene grupos/records
        if (Array.isArray(n.data)) {
            for (const item of n.data) {
                walk(item);
            }
        }

        // Algunas variantes: n.records
        if (Array.isArray(n.records)) {
            for (const r of n.records) {
                walk(r);
            }
        }
    };

    walk(node);
    return out;
}

async function expandAll(controller) {
    if (controller.props?.resModel !== "repair.order") return;

    const root = controller.model?.root;
    if (!root) return;

    const groups = collectGroups(root);
    if (!groups.length) return;

    const MAX_GROUPS = 200;
    if (groups.length > MAX_GROUPS) return;

    for (const g of groups) {
        const folded = g.isFolded ?? g.folded ?? (g.isOpen === false);
        if (!folded) continue;

        // Distintas firmas según versión/build: probamos ambas
        if (controller.model?.toggleGroup) {
            try {
                await controller.model.toggleGroup(g);
                continue;
            } catch (_) {}
            try {
                await controller.model.toggleGroup(g.id);
                continue;
            } catch (_) {}
        }

        if (controller.model?.root?.toggleGroup) {
            try {
                await controller.model.root.toggleGroup(g);
                continue;
            } catch (_) {}
            try {
                await controller.model.root.toggleGroup(g.id);
                continue;
            } catch (_) {}
        }
    }
}

patch(ListController.prototype, {
    setup(...args) {
        if (_setup) _setup.call(this, ...args);

        // 1) al montar
        onMounted(() => {
            // pequeño delay para asegurar que el listado ya está “pintado”
            setTimeout(() => expandAll(this), 0);
        });

        // 2) cada vez que cambian props (p.ej. agrupación, búsqueda, recarga)
        onWillUpdateProps(() => {
            setTimeout(() => expandAll(this), 0);
        });
    },
});
