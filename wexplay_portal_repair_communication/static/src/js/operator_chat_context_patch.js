/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useEffect } from "@odoo/owl";
import { ChatWindow } from "@mail/core/common/chat_window";

patch(ChatWindow.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        Object.assign(this.state, {
            wexPortalRepairSidebar: null,
            wexPortalRepairSidebarLoading: false,
            wexPortalRepairSidebarOpen: true,
        });

        useEffect(
            () => {
                this.state.wexPortalRepairSidebar = null;
                this.state.wexPortalRepairSidebarOpen = true;
                if (this.isWexPortalRepairOperatorThread()) {
                    this.loadWexPortalRepairSidebar();
                }
            },
            () => [this.thread?.model, this.thread?.id]
        );
    },

    isWexPortalRepairOperatorThread() {
        return this.thread?.model === "discuss.channel" && !!this.thread?.id;
    },

    hasWexPortalRepairSidebar() {
        return Boolean(this.state.wexPortalRepairSidebar?.enabled);
    },

    async loadWexPortalRepairSidebar(force = false) {
        if (!this.isWexPortalRepairOperatorThread()) {
            this.state.wexPortalRepairSidebar = null;
            return;
        }
        if (this.state.wexPortalRepairSidebarLoading && !force) {
            return;
        }
        this.state.wexPortalRepairSidebarLoading = true;
        try {
            this.state.wexPortalRepairSidebar = await this.orm.call(
                "discuss.channel",
                "get_wex_portal_repair_sidebar_values",
                [[this.thread.id]]
            );
        } finally {
            this.state.wexPortalRepairSidebarLoading = false;
        }
    },

    toggleWexPortalRepairSidebar() {
        this.state.wexPortalRepairSidebarOpen = !this.state.wexPortalRepairSidebarOpen;
    },

    async openWexPortalRepairRecord() {
        if (!this.isWexPortalRepairOperatorThread()) {
            return;
        }
        const action = await this.orm.call(
            "discuss.channel",
            "action_open_wex_portal_repair",
            [[this.thread.id]]
        );
        if (action) {
            this.action.doAction(action);
        }
    },

    async openWexPortalRepairCustomer() {
        if (!this.isWexPortalRepairOperatorThread()) {
            return;
        }
        const action = await this.orm.call(
            "discuss.channel",
            "action_open_wex_portal_customer",
            [[this.thread.id]]
        );
        if (action) {
            this.action.doAction(action);
        }
    },
});
