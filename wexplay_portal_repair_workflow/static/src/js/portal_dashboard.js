/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

class WexPortalDashboard extends Component {
    static template = "wexplay_portal_repair_workflow.PortalDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            periodDays: this.props.action?.params?.period_days || 7,
            error: "",
            data: this.getEmptyDashboardData(),
        });

        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    getEmptyDashboardData() {
        return {
            title: _t("Portal clientes"),
            subtitle: "",
            period_options: [],
            generated_at: "",
            attention_cards: [],
            summary_cards: [],
            conversation_cards: [],
            activity_preview: {
                title: _t("Actividad reciente"),
                rows: [],
                empty_message: _t("Todavía no hay actividad portal registrada."),
                open_all_action: null,
            },
            quick_actions: [],
        };
    }

    get title() {
        return this.state.data?.title || _t("Portal clientes");
    }

    get subtitle() {
        return this.state.data?.subtitle || "";
    }

    get periodOptions() {
        return this.state.data?.period_options || [];
    }

    get attentionCards() {
        return this.state.data?.attention_cards || [];
    }

    get summaryCards() {
        return this.state.data?.summary_cards || [];
    }

    get conversationCards() {
        return this.state.data?.conversation_cards || [];
    }

    get quickActions() {
        return this.state.data?.quick_actions || [];
    }

    get activityPreview() {
        return this.state.data?.activity_preview || { rows: [] };
    }

    get generatedAtLabel() {
        return this.formatDateTimeValue(this.state.data?.generated_at);
    }

    async loadDashboard(periodDays = this.state.periodDays) {
        this.state.loading = true;
        this.state.periodDays = periodDays;
        this.state.error = "";
        try {
            this.state.data = await this.orm.call(
                "wex.portal.dashboard",
                "get_dashboard_data",
                [periodDays]
            );
        } catch (error) {
            this.notification.add(
                _t("No se pudo cargar el dashboard del portal."),
                { type: "danger" }
            );
            this.state.error = error?.message || _t("No se pudo cargar el dashboard.");
        } finally {
            this.state.loading = false;
        }
    }

    async changePeriod(days) {
        if (this.state.loading || this.state.periodDays === days) {
            return;
        }
        await this.loadDashboard(days);
    }

    async openAction(action) {
        if (!action) {
            return;
        }
        await this.action.doAction(action);
    }

    getCardClass(card) {
        return "wex_kb_stat_card d-flex flex-column align-items-center justify-content-center text-center gap-2";
    }

    getHandledBadgeClass(row) {
        const state = row.handled_state || "pending";
        if (state === "pending") {
            return "wex_kb_badge is-draft";
        }
        if (state === "in_progress") {
            return "wex_kb_badge is-visibility-group";
        }
        if (state === "done") {
            return "wex_kb_badge is-published";
        }
        return "wex_kb_badge is-muted";
    }

    formatDateTimeValue(value) {
        if (!value) {
            return "";
        }
        try {
            return formatDateTime(deserializeDateTime(value));
        } catch {
            return value;
        }
    }

    formatMonetaryValue(row) {
        if (row.amount_total === false || row.amount_total === null || row.amount_total === undefined) {
            return "";
        }
        const formatted = new Intl.NumberFormat("es-ES", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(row.amount_total);
        const currencyName = Array.isArray(row.currency_id) ? row.currency_id[1] : "";
        return currencyName ? `${formatted} ${currencyName}` : formatted;
    }
}

registry.category("actions").add(
    "wexplay_portal_repair_workflow.portal_dashboard",
    WexPortalDashboard
);
