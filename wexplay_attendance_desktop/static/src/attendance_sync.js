/** @odoo-module **/

import {onWillUnmount} from "@odoo/owl";
import {patch} from "@web/core/utils/patch";
import {useBus, useService} from "@web/core/utils/hooks";
import {ActivityMenu} from "@hr_attendance/components/attendance_menu/attendance_menu";
import {AppsMenu} from "@web_responsive/components/apps_menu/apps_menu.esm";
import {AttendanceCard} from "./attendance_card";
import {ATTENDANCE_UPDATED} from "./attendance_service";

AppsMenu.components = {...AppsMenu.components, AttendanceCard};

patch(ActivityMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.desktopAttendance = useService("wexplay_attendance_desktop");
        this._desktopAttendanceMounted = true;
        onWillUnmount(() => { this._desktopAttendanceMounted = false; });
        useBus(this.env.bus, ATTENDANCE_UPDATED, () => {
            this.searchReadEmployee();
        });
    },

    async signInOut() {
        this.dropdown.close();
        // El bloqueo y la comprobación previa son comunes a los dos controles.
        if (this.desktopAttendance.state.busy || this.desktopAttendance.state.refreshing) {
            return;
        }
        const expected = this.employee;
        if (!this.desktopAttendance.state.ready) {
            await this.desktopAttendance.refresh();
        }
        await this.desktopAttendance.signInOut(expected);
        const {error, message} = this.desktopAttendance.state;
        if (this._desktopAttendanceMounted && (error || message)) {
            this.notification.add(error || message, {type: error ? "danger" : "info"});
        }
    },
});
