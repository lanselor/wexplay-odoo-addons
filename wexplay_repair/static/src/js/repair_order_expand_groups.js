/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { RelationalModel } from "@web/model/relational_model/relational_model";

patch(RelationalModel.DynamicRecordList.prototype, {
    /**
     * @override
     */
    setup(params) {
        // Verificamos si el modelo es el de reparaciones
        if (params.resModel === "repair.order") {
            // Forzamos que el estado inicial de 'expandido' sea verdadero
            // Esto anula el comportamiento por defecto de nacer plegado
            if (params.groupBy && params.groupBy.length > 0) {
                this.isFolded = false; 
            }
        }
        return super.setup(...params);
    },

    /**
     * Este método es el que decide si un grupo recién cargado está plegado.
     * Al devolver siempre false para repair.order, se mostrarán abiertos.
     */
    _isFolded(id) {
        if (this.resModel === "repair.order") {
            return false;
        }
        return super._isFolded(...arguments);
    }
});