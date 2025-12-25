/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { RelationalModel } from "@web/model/relational_model/relational_model";

patch(RelationalModel.DynamicRecordList.prototype, {
    /**
     * @override
     */
    setup(params) {
        // Ejecutamos el original primero usando super.setup(params)
        // sin el operador spread (...) que estaba dando error
        const result = super.setup(params);

        // Aplicamos nuestra lógica si es el modelo de reparaciones
        if (params && params.resModel === "repair.order") {
            // Si hay una agrupación activa, marcamos el estado como NO plegado
            if (params.groupBy && params.groupBy.length > 0) {
                this.isFolded = false;
            }
        }
        return result;
    },

    /**
     * Forzamos que el sistema detecte que NO debe estar plegado
     */
    _isFolded(id) {
        if (this.resModel === "repair.order") {
            return false;
        }
        return super._isFolded(...arguments);
    }
});