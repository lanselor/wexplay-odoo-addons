/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class ItMaintenanceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: {
                counts: {
                    customers: 0,
                    coverages: 0,
                    assets: 0,
                    open_activities: 0,
                    services: 0,
                    software: 0,
                    networks: 0,
                },
                upcoming_visits: [],
                overdue_visits: [],
                customers_without_next_visit: [],
                problematic_assets: [],
                expiring_services: [],
                recent_visits: [],
            },
        });

        onWillStart(async () => {
            await this.load();
        });
    }

    async load() {
        this.state.loading = true;
        this.state.data = await this.orm.call("wex.it.maintenance.visit", "get_dashboard_data", []);
        this.state.loading = false;
    }

    async openAction(xmlId) {
        await this.action.doAction(xmlId);
    }

    async openRecord(model, recordId) {
        if (model === "res.partner") {
            const action = await this.orm.call("res.partner", "action_open_it_workspace", [[recordId]]);
            await this.action.doAction(action);
            return;
        }
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: recordId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

ItMaintenanceDashboard.template = "wex_it_maintenance.ItMaintenanceDashboard";

registry.category("actions").add("wex_it_maintenance_dashboard", ItMaintenanceDashboard);
