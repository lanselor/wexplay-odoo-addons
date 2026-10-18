/** @odoo-module **/

import {Component, onMounted, onWillUnmount, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {registry} from "@web/core/registry";
import {deserializeDateTime} from "@web/core/l10n/dates";

export class AttendanceCard extends Component {
    static template = "wexplay_attendance_desktop.AttendanceCard";
    static props = {};

    setup() {
        this.attendance = useService("wexplay_attendance_desktop");
        this.state = useState(this.attendance.state);
        this.formatHours = registry.category("formatters").get("float_time");
        const refresh = () => {
            if (!document.hidden && !this.state.busy) {
                this.attendance.refresh();
            }
        };
        onMounted(() => {
            refresh();
            this.timer = setInterval(refresh, 60000);
            window.addEventListener("focus", refresh);
            document.addEventListener("visibilitychange", refresh);
        });
        onWillUnmount(() => {
            clearInterval(this.timer);
            window.removeEventListener("focus", refresh);
            document.removeEventListener("visibilitychange", refresh);
        });
    }

    get isVisible() {
        return Boolean(this.state.employee.id && this.state.employee.display_systray);
    }

    get checkedIn() {
        return this.state.employee.attendance_state === "checked_in";
    }

    get entryTime() {
        const value = this.state.employee.last_check_in;
        return value ? deserializeDateTime(value).toLocaleString(luxon.DateTime.DATETIME_SHORT) : "";
    }

    get hoursToday() {
        return this.formatHours(this.state.employee.hours_today || 0);
    }

    async signInOut() {
        await this.attendance.signInOut();
    }

    async refresh() {
        await this.attendance.refresh();
    }
}
