/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";

/**
 * Wexplay: auto-desplegar todos los grupos en la lista de repair.order
 * cuando la vista está agrupada (por fecha u otros campos).
 *
 * Nota: Abrir muchos grupos puede ser pesado si hay cientos.
 */
patch(ListController.prototype, "wexplay_repair.expand_all_groups", {
    async mounted() {
        // Llama al mounted original
        if (super.mounted) {
            await super.mounted();
        }

        // Solo en repair.order
        if (this.props?.resModel !== "repair.order") return;

        // Espera un tick para que el modelo/render termine de estabilizarse
        setTimeout(async () => {
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
                    // En distintas versiones la bandera puede llamarse distinto:
                    // isFolded / folded / isOpen, etc. Probamos de forma defensiva.
                    const folded =
                        g.isFolded ?? g.folded ?? (g.isOpen === false);

                    if (folded) {
                        // toggleGroup suele existir en el modelo en listas agrupadas
                        if (this.model?.toggleGroup) {
                            await this.model.toggleGroup(g);
                        } else if (this.model?.root?.toggleGroup) {
                            await this.model.root.toggleGroup(g);
                        } else {
                            // Si no existe, no podemos forzarlo desde aquí
                            break;
                        }
                    }
                }
            } catch (e) {
                // Silencioso para no romper la UI si Odoo cambia internals
                // (pero si quieres, puedes console.log(e))
            }
        }, 0);
    },
});
