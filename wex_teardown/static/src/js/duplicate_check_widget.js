/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const CHUNK_SIZE = 3;

class WexTeardownDuplicateCheckWidget extends Component {
    static template = "wex_teardown.DuplicateCheckWidget";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            running: false,
            progress: this.props.record.data.duplicate_check_progress || 0,
            processed: this.props.record.data.duplicate_check_processed || 0,
            total: this.props.record.data.duplicate_check_total || 0,
            message: this.props.record.data.duplicate_check_message || "",
            status: this.props.record.data.duplicate_check_state || "idle",
        });
        this.isUnmounted = false;

        onWillUnmount(() => {
            this.isUnmounted = true;
        });
    }

    get canRun() {
        return ["template_loaded", "review"].includes(this.props.record.data.state);
    }

    get progressValue() {
        return Math.max(0, Math.min(100, this.state.progress || 0));
    }

    get progressClass() {
        if (this.state.status === "error") {
            return "bg-danger";
        }
        if (this.state.status === "done") {
            return "bg-success";
        }
        return "progress-bar-striped progress-bar-animated";
    }

    get counterLabel() {
        if (!this.state.total) {
            return "";
        }
        return `${this.state.processed}/${this.state.total}`;
    }

    get progressLabel() {
        return `${this.progressValue}%`;
    }

    async onRunDuplicateCheck() {
        if (this.state.running || !this.props.record.resId || !this.canRun) {
            return;
        }
        this.state.running = true;
        try {
            let payload = await this.orm.call(
                "wex.teardown.batch",
                "action_start_duplicate_check",
                [[this.props.record.resId]],
                { chunk_size: CHUNK_SIZE }
            );
            this._applyPayload(payload);
            while (!this.isUnmounted && payload.state === "running") {
                payload = await this.orm.call(
                    "wex.teardown.batch",
                    "action_process_duplicate_check_chunk",
                    [[this.props.record.resId]],
                    { chunk_size: payload.chunk_size || CHUNK_SIZE }
                );
                this._applyPayload(payload);
            }
            if (this.isUnmounted) {
                return;
            }
            if (payload.state === "done") {
                this.notification.add(payload.message || "Coincidencias revisadas.", { type: "success" });
                await this._refreshView();
            } else if (payload.state === "error") {
                this.notification.add(payload.message || "No se pudo completar la búsqueda.", {
                    type: "danger",
                });
            }
        } catch (error) {
            if (!this.isUnmounted) {
                this.state.status = "error";
                this.state.message = error?.message || String(error);
                this.notification.add(this.state.message, { type: "danger" });
            }
        } finally {
            if (!this.isUnmounted) {
                this.state.running = false;
            }
        }
    }

    _applyPayload(payload) {
        this.state.status = payload.state || "idle";
        this.state.progress = payload.progress || 0;
        this.state.processed = payload.processed || 0;
        this.state.total = payload.total || 0;
        this.state.message = payload.message || "";
    }

    async _refreshView() {
        try {
            if (this.props.record?.model?.root?.load) {
                await this.props.record.model.root.load();
                return;
            }
            if (this.props.record?.load) {
                await this.props.record.load();
                return;
            }
        } catch {
            // Fallback below.
        }
        await this.action.doAction({ type: "ir.actions.client", tag: "reload" });
    }
}

export const wexTeardownDuplicateCheckWidget = {
    component: WexTeardownDuplicateCheckWidget,
    displayName: "Wex Teardown Duplicate Check",
    supportedTypes: ["integer"],
};

registry.category("fields").add("wex_teardown_duplicate_check", wexTeardownDuplicateCheckWidget);
