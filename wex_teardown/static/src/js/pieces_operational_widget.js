/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

function cloneDraft(row) {
    if (!row) {
        return {
            part_number: "",
            quantity: 1,
            name_final: "",
            missing_part_number_confirmed: false,
        };
    }
    return {
        part_number: row.part_number || "",
        quantity: row.quantity ?? 1,
        name_final: row.name_suggested || row.name_final || "",
        missing_part_number_confirmed: Boolean(row.missing_part_number_confirmed),
    };
}

class WexTeardownPiecesOperationalWidget extends Component {
    static template = "wex_teardown.PiecesOperationalWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            rows: [],
            expandedId: null,
            drafts: {},
            savingId: null,
            actionId: null,
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
            this.state.loading = false;
            return;
        }
        this.state.loading = true;
        const payload = await this.orm.call("wex.teardown.batch", "action_get_operational_piece_rows", [[this.batchId]]);
        this.state.rows = payload.rows || [];
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

    handlePartNumberInput(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        this.updateDraft(rowId, "part_number", ev.currentTarget.value);
    }

    handleMissingPartNumberToggle(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        this.updateDraft(rowId, "missing_part_number_confirmed", ev.currentTarget.checked);
    }

    handleQuantityInput(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        this.updateDraft(rowId, "quantity", ev.currentTarget.value);
    }

    handleNameInput(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        this.updateDraft(rowId, "name_final", ev.currentTarget.value);
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
                "action_save_operational_review",
                [[row.id], draft]
            );
            this._replaceRow(updated);
            delete this.state.drafts[row.id];
            this.state.expandedId = null;
            this.notification.add("Pieza actualizada.", { type: "success" });
        } finally {
            this.state.savingId = null;
        }
    }

    async markOk(ev) {
        const row = this.getRow(ev.currentTarget.dataset.rowId);
        if (!row) {
            return;
        }
        await this.orm.call("wex.teardown.line", "action_mark_qc_ok", [[row.id]]);
        await this.loadRows();
        await this._refreshParentRecord();
    }

    async openReject(ev) {
        const row = this.getRow(ev.currentTarget.dataset.rowId);
        if (!row) {
            return;
        }
        const action = await this.orm.call("wex.teardown.line", "action_open_reject_wizard", [[row.id]]);
        await this.action.doAction(action, {
            onClose: async () => {
                await this.loadRows();
                await this._refreshParentRecord();
            },
        });
    }

    async chooseExisting(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        const productId = Number(ev.currentTarget.dataset.productId);
        const updateName = ev.currentTarget.dataset.updateName === "1";
        const updated = await this.orm.call(
            "wex.teardown.line",
            "action_choose_existing_product",
            [[rowId], productId, updateName]
        );
        this._replaceRow(updated);
        this.notification.add(
            updateName ? "Producto existente seleccionado y nombre preparado para actualizar." : "Producto existente seleccionado.",
            { type: "success" }
        );
    }

    async openProduct(ev) {
        const rowId = Number(ev.currentTarget.dataset.rowId);
        const productId = Number(ev.currentTarget.dataset.productId);
        const action = await this.orm.call("wex.teardown.line", "action_open_existing_product", [[rowId], productId]);
        await this.action.doAction(action);
    }

    _replaceRow(updated) {
        const index = this.state.rows.findIndex((row) => row.id === updated.id);
        if (index >= 0) {
            this.state.rows.splice(index, 1, updated);
        }
    }

    async _refreshParentRecord() {
        try {
            if (this.props.record?.model?.root?.load) {
                await this.props.record.model.root.load();
                return;
            }
            if (this.props.record?.load) {
                await this.props.record.load();
            }
        } catch {
            // El widget sigue siendo funcional aunque el refresco fino falle.
        }
    }
}

export const wexTeardownPiecesOperationalWidget = {
    component: WexTeardownPiecesOperationalWidget,
    displayName: "Wex Teardown Pieces Operational Widget",
    supportedTypes: ["integer"],
};

registry.category("fields").add("wex_teardown_pieces_operational", wexTeardownPiecesOperationalWidget);
