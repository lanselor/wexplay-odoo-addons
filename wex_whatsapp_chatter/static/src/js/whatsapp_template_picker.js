/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { useState } from "@odoo/owl";

const FILTERS_BY_MODEL = {
    "repair.order": [
        { value: "all", label: "Todas", icon: "fa-th-large" },
        { value: "repair_budget", label: "Presupuesto", icon: "fa-eur" },
        { value: "repair_ready", label: "Listo", icon: "fa-check-circle" },
        { value: "repair_pending", label: "Pendiente", icon: "fa-clock-o" },
        { value: "repair_non_repairable", label: "No reparable", icon: "fa-ban" },
        { value: "repair_b2b", label: "B2B", icon: "fa-building" },
        { value: "repair_other", label: "Otros", icon: "fa-ellipsis-h" },
    ],
    "sale.order": [
        { value: "all", label: "Todas", icon: "fa-th-large" },
        { value: "sale_quote", label: "Presupuesto", icon: "fa-file-text-o" },
        { value: "sale_followup", label: "Seguimiento", icon: "fa-refresh" },
        { value: "sale_other", label: "Otros", icon: "fa-ellipsis-h" },
    ],
    "account.move": [
        { value: "all", label: "Todas", icon: "fa-th-large" },
        { value: "account_invoice", label: "Factura", icon: "fa-file-text-o" },
        { value: "account_payment", label: "Cobro", icon: "fa-credit-card" },
        { value: "account_other", label: "Otros", icon: "fa-ellipsis-h" },
    ],
    "res.partner": [
        { value: "all", label: "Todas", icon: "fa-th-large" },
        { value: "partner_general", label: "General", icon: "fa-user" },
        { value: "partner_followup", label: "Seguimiento", icon: "fa-commenting-o" },
    ],
    "mrw.shipping.shipment": [
        { value: "all", label: "Todas", icon: "fa-th-large" },
        { value: "mrw_shipping", label: "MRW", icon: "fa-truck" },
    ],
};

class WexWhatsappTemplatePicker extends Many2OneField {
    static template = "wex_whatsapp_chatter.TemplatePicker";

    setup() {
        super.setup(...arguments);
        this.filterState = useState({ value: "all" });
    }

    get filterButtons() {
        return FILTERS_BY_MODEL[this.props.record.data.res_model] || [];
    }

    getDomain() {
        const domain = super.getDomain() || [];
        if (this.filterState.value === "all") {
            return domain;
        }
        return [...domain, ["context_group", "=", this.filterState.value]];
    }

    onQuickFilterClick(ev) {
        ev.preventDefault();
        this.filterState.value = ev.currentTarget.dataset.filter;

        // Si el desplegable ya estaba abierto, repite la misma búsqueda con el nuevo dominio.
        const input = this.autocompleteContainerRef.el?.querySelector("input");
        if (input) {
            input.dispatchEvent(new Event("input", { bubbles: true }));
        }
    }
}

registry.category("fields").add("wex_whatsapp_template_picker", {
    ...many2OneField,
    component: WexWhatsappTemplatePicker,
});
