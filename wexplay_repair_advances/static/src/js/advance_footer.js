/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.wexAdvanceOrm = useService("orm");
        this.wexAdvanceAction = useService("action");
        this.wexAdvances = useState({ open: false, loading: false, summary: null });
    },
    async toggleWexAdvances() {
        this.wexAdvances.open = !this.wexAdvances.open;
        if (!this.wexAdvances.open || this.wexAdvances.loading) {
            return;
        }
        if (!(await this.props.record.save())) {
            this.wexAdvances.open = false;
            return;
        }
        this.wexAdvances.loading = true;
        try {
            this.wexAdvances.summary = await this.wexAdvanceOrm.call(
                "repair.order", "get_advance_summary", [[this.props.record.resId]]
            );
        } finally {
            this.wexAdvances.loading = false;
        }
    },
    async openWexAdvanceAction(method) {
        if (!(await this.props.record.save())) {
            return;
        }
        const action = await this.wexAdvanceOrm.call(
            "repair.order", method, [[this.props.record.resId]]
        );
        this.wexAdvances.open = false;
        return this.wexAdvanceAction.doAction(action);
    },
});
