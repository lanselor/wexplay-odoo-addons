/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useEffect } from "@odoo/owl";

const _setup = ListController.prototype.setup;

function isFolded(g) {
    // flags comunes en distintas builds
    if (g?.isFolded !== undefined) return !!g.isFolded;
    if (g?.folded !== undefined) return !!g.folded;
    if (g?.isOpen !== undefined) return g.isOpen === false;
    if (g?.open !== undefined) return g.open === false;
    return false;
}

async function expandAll(model, groups, limit = 200) {
    if (!groups?.length) return;
    let count = 0;

    for (const g of groups) {
        if (count >= limit) return;

        if (isFolded(g)) {
            try {
                await model.toggleGroup(g);
            } catch (e) {
                // fallback por si espera id/datapoint
                try { await model.toggleGroup(g.id); } catch (_) {}
                try { await model.toggleGroup(g.resId); } catch (_) {}
            }
            count++;
        }

        // subgrupos (si existen)
        if (g?.groups?.length) {
            await expandAll(model, g.groups, limit - count);
        }
    }
}

patch(ListController.prototype, {
    setup() {
        if (_setup) _setup.call(this, ...arguments);

        useEffect(() => {
            if (this.props?.resModel !== "repair.order") return;

            // Espera a que el modelo/render se estabilicen
            setTimeout(async () => {
                const root = this.model?.root;
                const groups = root?.groups;
                await expandAll(this.model, groups, 300);
            }, 0);
        }, () => [this.model?.root]);
    },
});
