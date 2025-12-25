/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { useEffect } from "@odoo/owl";

const _setup = ListController.prototype.setup;

patch(ListController.prototype, {
    setup() {
        if (_setup) _setup.call(this, ...arguments);

        const expand = async () => {
            if (this.props?.resModel !== "repair.order") return;

            const root = this.model?.root;
            const groups = root?.groups;
            if (!groups?.length) return;

            for (const group of groups) {
                if (group?.isFolded) {
                    try {
                        await this.model.toggleGroup(group);
                    } catch (e) {
                        // fallback por si esta build espera id/datapoint
                        try {
                            await this.model.toggleGroup(group.id);
                        } catch (_) {}
                    }
                }
            }
        };

        useEffect(
            () => {
                // Espera un tick para que OWL/render y el modelo se estabilicen
                setTimeout(() => { expand(); }, 0);
            },
            // Dependencia por "estado" que sí cambia cuando el root se recrea/cambia de grouping
            () => [this.model?.root]
        );
    },
});
