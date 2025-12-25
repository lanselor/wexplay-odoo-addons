/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted } from "@odoo/owl";

/**
 * Wexplay: auto-desplegar todos los grupos en la lista de repair.order
 * cuando la vista está agrupada (por fecha u otros campos).
 *
 * Nota: Abrir muchos grupos puede ser pesado si hay cientos.
 */
patch(ListController.prototype, {
    setup() {
        this._super(...arguments);

        onMounted(async () => {
            // Solo en repair.order
            if (this.props?.resModel !== "repair.order") return;

            try {
                const root = this.model?.root;
                if (!root) return;

                // Si no hay grupos, no está agrupada la lista
                const groups = root.groups || [];
                if (!groups.length) return;

                // Guard-rail opcional: evita abrir demasiados grupos de golpe
                const MAX_GROUPS = 200;
                if (groups.length > MAX_GROUPS) return;

                // Intenta desplegar todos los grupos "plegados"
                for (const g of groups) {
                    const folded =
                        g.isFolded ?? g.folded ?? (g.isOpen === false);

                    if (folded) {
                        if (this.model?.toggleGroup) {
                            await this.model.toggleGroup(g);
                        } else if (this.model?.root?.toggleGroup) {
                            await this.model.root.toggleGroup(g);
                        } else {
                            break;
                        }
                    }
                }
            } catch (e) {
                // Si quieres depurar:
                // console.error("Wexplay expand groups failed:", e);
            }
        });
    },
});
