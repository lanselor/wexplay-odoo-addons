/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

function cloneDraft(row) {
    return {
        list_price: row.list_price ?? 0,
        pvp_tax_included: row.pvp_tax_included ?? 0,
        standard_price: row.standard_price ?? 0,
        tax_ids: [...(row.tax_ids || [])],
        price_source: "list_price",
    };
}

function parseNumber(value) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : null;
}

function roundAmount(value) {
    return Math.round(value * 100) / 100;
}

class WexTeardownDataCompletionWidget extends Component {
    static template = "wex_teardown.DataCompletionWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            rows: [],
            taxOptions: [],
            expandedId: null,
            drafts: {},
            savingId: null,
        });

        onMounted(async () => {
            await this.loadRows();
        });
    }

    get batchId() {
        return this.props.record.resId;
    }

    async loadRows() {
        if (!this.batchId) {
            this.state.rows = [];
            this.state.taxOptions = [];
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        const payload = await this.orm.call("wex.teardown.batch", "action_get_data_completion_rows", [[this.batchId]]);
        this.state.rows = payload.rows || [];
        this.state.taxOptions = payload.tax_options || [];
        this.state.loading = false;
        if (this.state.expandedId && !this.state.rows.find((row) => row.id === this.state.expandedId)) {
            this.state.expandedId = null;
        }
    }

    isExpanded(rowId) {
        return this.state.expandedId === rowId;
    }

    getRow(rowId) {
        return this.state.rows.find((item) => item.id === Number(rowId));
    }

    getDraft(row) {
        if (!this.state.drafts[row.id]) {
            this.state.drafts[row.id] = cloneDraft(row);
        }
        return this.state.drafts[row.id];
    }

    toggleExpand(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        this.state.expandedId = this.isExpanded(rowId) ? null : rowId;
    }

    updateDraft(rowId, fieldName, value) {
        if (!this.state.drafts[rowId]) {
            const row = this.state.rows.find((item) => item.id === rowId);
            if (!row) {
                return;
            }
            this.state.drafts[rowId] = cloneDraft(row);
        }
        this.state.drafts[rowId][fieldName] = value;
    }

    handlePriceInput(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        this._syncPriceDraft(rowId, "list_price", ev.currentTarget.value);
    }

    handlePvpInput(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        this._syncPriceDraft(rowId, "pvp_tax_included", ev.currentTarget.value);
    }

    handleCostInput(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        this.updateDraft(rowId, "standard_price", ev.currentTarget.value);
    }

    updateTaxSelection(rowId, ev) {
        const values = Array.from(ev.currentTarget.selectedOptions).map((option) => Number(option.value));
        this.updateDraft(rowId, "tax_ids", values);
    }

    cancelEdit(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        delete this.state.drafts[rowId];
        this.state.expandedId = null;
    }

    async saveRow(ev) {
        const row = this.getRow(ev.currentTarget.dataset.rowId);
        if (!row) {
            return;
        }
        const draft = this.getDraft(row);
        this.state.savingId = row.id;
        try {
            const updated = await this.orm.call(
                "wex.teardown.line",
                "action_save_data_completion_review",
                [[row.id], draft]
            );
            this._replaceRow(updated);
            delete this.state.drafts[row.id];
            this.state.expandedId = null;
            this.notification.add("Datos de precio actualizados.", { type: "success" });
        } finally {
            this.state.savingId = null;
        }
    }

    isTaxSelected(row, taxId) {
        return this.getDraft(row).tax_ids.includes(taxId);
    }

    _syncPriceDraft(rowId, sourceField, rawValue) {
        const row = this.getRow(rowId);
        if (!row) {
            return;
        }
        const draft = this.getDraft(row);
        const sourceAmount = parseNumber(rawValue);
        draft[sourceField] = rawValue;
        draft.price_source = sourceField === "pvp_tax_included" ? "pvp" : "list_price";
        const percent = this._getPercentTaxRate(row);
        if (sourceAmount === null || percent === null) {
            const counterpartField = sourceField === "pvp_tax_included" ? "list_price" : "pvp_tax_included";
            draft[counterpartField] = rawValue === "" ? "" : draft[counterpartField];
            return;
        }
        if (sourceField === "list_price") {
            draft.pvp_tax_included = roundAmount(sourceAmount * (1 + (percent / 100)));
            return;
        }
        draft.list_price = roundAmount(sourceAmount / (1 + (percent / 100)));
    }

    _getPercentTaxRate(row) {
        const taxDetails = row.tax_details || [];
        if (!taxDetails.length) {
            return 0;
        }
        if (taxDetails.some((tax) => tax.amount_type !== "percent")) {
            return null;
        }
        return taxDetails.reduce((total, tax) => total + (tax.amount || 0), 0);
    }

    _replaceRow(updated) {
        const index = this.state.rows.findIndex((row) => row.id === updated.id);
        if (index >= 0) {
            this.state.rows.splice(index, 1, updated);
        }
    }
}

export const wexTeardownDataCompletionWidget = {
    component: WexTeardownDataCompletionWidget,
    displayName: "Wex Teardown Data Completion Widget",
    supportedTypes: ["integer"],
};

registry.category("fields").add("wex_teardown_data_completion", wexTeardownDataCompletionWidget);
