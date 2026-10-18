/** @odoo-module **/

import {reactive} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {rpc} from "@web/core/network/rpc";
import {isIosApp} from "@web/core/browser/feature_detection";
import {_t} from "@web/core/l10n/translation";

export const ATTENDANCE_UPDATED = "WEXPLAY:ATTENDANCE_UPDATED";

export class DesktopAttendance {
    constructor(bus) {
        this.bus = bus;
        this.state = reactive({
            employee: {}, ready: false, busy: false, refreshing: false,
            message: "", error: "",
        });
        this._refreshPromise = null;
    }

    _setEmployee(employee) {
        const previous = this.state.employee;
        if (previous.id !== employee.id ||
            previous.attendance_state !== employee.attendance_state ||
            previous.last_check_in !== employee.last_check_in) {
            this.state.message = "";
        }
        this.state.employee = employee;
        this.state.ready = true;
        this.state.error = "";
        this.bus.trigger(ATTENDANCE_UPDATED);
    }

    async refresh() {
        if (this._refreshPromise) {
            return this._refreshPromise;
        }
        this.state.refreshing = true;
        this._refreshPromise = this._readEmployee();
        try {
            return await this._refreshPromise;
        } finally {
            this.state.refreshing = false;
            this._refreshPromise = null;
        }
    }

    async _readEmployee() {
        try {
            const employee = await rpc("/hr_attendance/attendance_user_data");
            this._setEmployee(employee);
            return employee;
        } catch {
            this.state.ready = false;
            this.state.message = "";
            this.state.error = _t("No se ha podido consultar el fichaje. Actualiza el estado antes de continuar.");
            return null;
        }
    }

    async signInOut(expected = this.state.employee) {
        if (this.state.busy || this.state.refreshing || !this.state.ready) {
            return;
        }
        if (!expected.id || !expected.display_systray) {
            return;
        }
        this.state.busy = true;
        this.state.message = "";
        this.state.error = "";
        try {
            const position = await this._getPosition();
            const current = await this.refresh();
            if (!current) {
                return;
            }
            if (current.id !== expected.id ||
                current.attendance_state !== expected.attendance_state ||
                current.last_check_in !== expected.last_check_in ||
                !current.display_systray) {
                this.state.message = _t("El estado ha cambiado. Revísalo antes de volver a fichar.");
                return;
            }
            const result = await rpc("/hr_attendance/systray_check_in_out", position);
            if (!result.id || result.id !== current.id ||
                !["checked_in", "checked_out"].includes(result.attendance_state) ||
                result.attendance_state === current.attendance_state) {
                throw new Error("Unexpected attendance response");
            }
            this._setEmployee(result);
            this.state.message = result.attendance_state === "checked_in"
                ? _t("Entrada registrada correctamente.")
                : _t("Salida registrada correctamente.");
        } catch {
            this.state.ready = false;
            this.state.error = _t("No se ha podido confirmar el fichaje. Actualiza el estado para comprobar si se ha registrado antes de repetirlo.");
        } finally {
            this.state.busy = false;
        }
    }

    async _getPosition() {
        if (isIosApp() || !navigator.onLine || !navigator.geolocation) {
            return {latitude: false, longitude: false};
        }
        return new Promise((resolve) => {
            const fallback = {latitude: false, longitude: false};
            const timer = setTimeout(() => resolve(fallback), 10500);
            const finish = (position) => {
                clearTimeout(timer);
                resolve(position);
            };
            try {
                navigator.geolocation.getCurrentPosition(
                    ({coords: {latitude, longitude}}) => finish({latitude, longitude}),
                    () => finish(fallback),
                    {enableHighAccuracy: true, timeout: 10000}
                );
            } catch {
                finish(fallback);
            }
        });
    }
}

registry.category("services").add("wexplay_attendance_desktop", {
    start(env) {
        return new DesktopAttendance(env.bus);
    },
});
