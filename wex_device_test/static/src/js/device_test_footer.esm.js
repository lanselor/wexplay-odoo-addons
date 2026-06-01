/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { onWillUnmount, useState } from "@odoo/owl";

const WEX_DEVICE_TEST_FOOTER_POLL_INTERVAL_MS = 4000;

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = this.orm || useService("orm");
        this.action = this.action || useService("action");
        this.notification = this.notification || useService("notification");
        this.wexDeviceTestFooterState = useState({
            isOpen: false,
            isLoading: false,
            isLoaded: false,
            error: "",
            data: null,
            liveNotice: "",
            liveNoticeTone: "info",
            lastUpdatedLabel: "",
        });
        this.wexDeviceTestFooterPollHandle = null;
        onWillUnmount(() => {
            this._stopWexDeviceTestFooterPolling();
        });
    },

    isWexDeviceTestFooterAvailable() {
        return (
            this._isWexRepairFormFooterEnabled() &&
            Boolean(this.props.record.resId) &&
            Boolean(this.props.record.data?.x_device_test_footer_allowed)
        );
    },

    getWexDeviceTestFooterButtonBadgeLabel() {
        const loadedLabel = this.wexDeviceTestFooterState.data?.state_label;
        if (loadedLabel) {
            return loadedLabel;
        }
        const state = this.props.record.data?.x_device_test_state;
        const labels = {
            pending_pairing: "Pendiente",
            paired: "Vinculada",
            in_progress: "En pruebas",
            completed: "Completado",
            cancelled: "Cancelado",
        };
        return labels[state] || "Sin run";
    },

    getWexDeviceTestFooterButtonBadgeClass() {
        const loadedTone = this.wexDeviceTestFooterState.data?.status_tone;
        const state = this.props.record.data?.x_device_test_state;
        const toneByState = {
            pending_pairing: "warning",
            paired: "success",
            in_progress: "info",
            completed: "success",
            cancelled: "neutral",
        };
        const tone = loadedTone || toneByState[state] || "neutral";
        return `wex-device-test-footer__status wex-device-test-footer__status--${tone}`;
    },

    async onWexDeviceTestFooterToggle() {
        if (!this.isWexDeviceTestFooterAvailable()) {
            return;
        }
        this.wexDeviceTestFooterState.isOpen = !this.wexDeviceTestFooterState.isOpen;
        if (!this.wexDeviceTestFooterState.isOpen) {
            this._stopWexDeviceTestFooterPolling();
            return;
        }
        if (
            !this.wexDeviceTestFooterState.isLoaded &&
            !this.wexDeviceTestFooterState.isLoading
        ) {
            await this.loadWexDeviceTestFooterData({ notifyOnChange: true });
        }
        this._startWexDeviceTestFooterPolling();
    },

    async loadWexDeviceTestFooterData(options = {}) {
        if (!this.props.record.resId || this.wexDeviceTestFooterState.isLoading) {
            return;
        }
        const { notifyOnChange = false, silentError = false } = options;
        const previousData = this.wexDeviceTestFooterState.data;
        this.wexDeviceTestFooterState.isLoading = true;
        this.wexDeviceTestFooterState.error = "";
        try {
            const data = await this.orm.call(
                "repair.order",
                "action_get_device_test_footer_data",
                [[this.props.record.resId]]
            );
            this._applyWexDeviceTestFooterData(data, previousData, { notifyOnChange });
        } catch (error) {
            this.wexDeviceTestFooterState.error = error?.message || "No se pudo cargar Conexión Android.";
            if (!silentError) {
                this.notification.add(this.wexDeviceTestFooterState.error, { type: "danger" });
            }
        } finally {
            this.wexDeviceTestFooterState.isLoading = false;
        }
    },

    async refreshWexDeviceTestFooterData() {
        this.wexDeviceTestFooterState.isLoaded = false;
        await this.loadWexDeviceTestFooterData({ notifyOnChange: true });
    },

    async onWexDeviceTestFooterStartRun() {
        await this._executeWexDeviceTestFooterDataCall("action_footer_start_device_test_run");
    },

    async onWexDeviceTestFooterRestartPairing() {
        await this._executeWexDeviceTestFooterDataCall("action_footer_restart_active_device_test_pairing");
    },

    async onWexDeviceTestFooterShowToken() {
        await this._executeWexDeviceTestFooterDataCall("action_footer_show_active_device_test_token");
    },

    async onWexDeviceTestFooterHideToken() {
        await this._executeWexDeviceTestFooterDataCall("action_footer_hide_active_device_test_token");
    },

    async onWexDeviceTestFooterOpenRun() {
        if (!this.props.record.resId) {
            return;
        }
        try {
            const action = await this.orm.call(
                "repair.order",
                "action_open_device_test_run",
                [[this.props.record.resId]]
            );
            if (action) {
                await this.action.doAction(action);
            }
        } catch (error) {
            this.notification.add(error?.message || "No se pudo abrir el run activo.", {
                type: "danger",
            });
        }
    },

    async _executeWexDeviceTestFooterDataCall(methodName) {
        if (!this.props.record.resId) {
            return;
        }
        const previousData = this.wexDeviceTestFooterState.data;
        this.wexDeviceTestFooterState.isLoading = true;
        this.wexDeviceTestFooterState.error = "";
        try {
            const data = await this.orm.call("repair.order", methodName, [[this.props.record.resId]]);
            this._applyWexDeviceTestFooterData(data, previousData, { notifyOnChange: true });
        } catch (error) {
            this.wexDeviceTestFooterState.error = error?.message || "No se pudo actualizar Conexión Android.";
            this.notification.add(this.wexDeviceTestFooterState.error, { type: "danger" });
        } finally {
            this.wexDeviceTestFooterState.isLoading = false;
        }
    },

    _applyWexDeviceTestFooterData(data, previousData = null, options = {}) {
        this.wexDeviceTestFooterState.data = data;
        this.wexDeviceTestFooterState.isLoaded = true;
        this.wexDeviceTestFooterState.lastUpdatedLabel = new Date().toLocaleTimeString("es-ES", {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit",
        });
        if (options.notifyOnChange) {
            this._notifyWexDeviceTestFooterTransitions(previousData, data);
        }
        if (this._shouldKeepWexDeviceTestFooterPolling(data)) {
            this._startWexDeviceTestFooterPolling();
        } else {
            this._stopWexDeviceTestFooterPolling();
        }
    },

    _notifyWexDeviceTestFooterTransitions(previousData, nextData) {
        if (!previousData) {
            return;
        }
        const stateChanged = previousData.state !== nextData.state;
        const sessionChanged = previousData.session_id !== nextData.session_id;
        if (!stateChanged && !sessionChanged) {
            return;
        }
        let message = "La conexión Android se ha actualizado automáticamente.";
        let tone = "info";
        if (
            previousData.state === "pending_pairing" &&
            ["paired", "in_progress", "completed"].includes(nextData.state)
        ) {
            message = "Vinculación Android completada automáticamente.";
            tone = "success";
        } else if (sessionChanged && nextData.session_name) {
            message = `Nueva sesión vinculada: ${nextData.session_name}.`;
            tone = "success";
        } else if (stateChanged && nextData.state_label) {
            message = `Estado Android actualizado a ${nextData.state_label}.`;
        }
        this.wexDeviceTestFooterState.liveNotice = message;
        this.wexDeviceTestFooterState.liveNoticeTone = tone;
        this.notification.add(message, { type: tone === "success" ? "success" : "info" });
    },

    _shouldKeepWexDeviceTestFooterPolling(data = null) {
        const currentData = data || this.wexDeviceTestFooterState.data;
        return (
            this.wexDeviceTestFooterState.isOpen &&
            Boolean(currentData) &&
            ["pending_pairing", "paired", "in_progress"].includes(currentData.state)
        );
    },

    _startWexDeviceTestFooterPolling() {
        if (this.wexDeviceTestFooterPollHandle || !this._shouldKeepWexDeviceTestFooterPolling()) {
            return;
        }
        this.wexDeviceTestFooterPollHandle = setInterval(async () => {
            if (!this._shouldKeepWexDeviceTestFooterPolling() || this.wexDeviceTestFooterState.isLoading) {
                if (!this._shouldKeepWexDeviceTestFooterPolling()) {
                    this._stopWexDeviceTestFooterPolling();
                }
                return;
            }
            await this.loadWexDeviceTestFooterData({
                notifyOnChange: true,
                silentError: true,
            });
        }, WEX_DEVICE_TEST_FOOTER_POLL_INTERVAL_MS);
    },

    _stopWexDeviceTestFooterPolling() {
        if (this.wexDeviceTestFooterPollHandle) {
            clearInterval(this.wexDeviceTestFooterPollHandle);
            this.wexDeviceTestFooterPollHandle = null;
        }
    },
});
