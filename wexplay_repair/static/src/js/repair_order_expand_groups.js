/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { onMounted } from "@odoo/owl";

// Guardamos referencia al setup original
const _setup = ListController.prototype.setup;

patch(ListController.prototype, {
    setup(...args) {
        // Llama al setup original (NO usar this._super en tu caso)
        if (_setup) {
            _setup.call(this, ...args);
        }

        onMounted(async () => {
            // Solo en repair.order
            if (this.props?.resModel !== "repair.order") return;

            try {
                const root = this.model?.root;
                if (!root) return;

                const groups = root.groups || [];
                if (!groups.length) return;

                const MAX_GROUPS = 200;
                if (groups.length > MAX_GROUPS) return;

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
                // Para depurar si vuelve a fallar:
                // console.error("Wexplay expand groups failed:", e);
            }
        });
    },
});
