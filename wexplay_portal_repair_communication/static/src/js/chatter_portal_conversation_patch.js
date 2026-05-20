/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useEffect, useState } from "@odoo/owl";
import { Chatter } from "@mail/chatter/web_portal/chatter";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.store = useState(useService("mail.store"));
        Object.assign(this.state, {
            portalConversationTab: "chatter",
            portalConversationLoading: false,
            portalConversation: null,
        });

        useEffect(
            () => {
                this.state.portalConversationTab = "chatter";
                this.state.portalConversation = null;
                if (this.isPortalConversationSupportedThread()) {
                    this.loadPortalConversationData();
                }
            },
            () => [this.props.threadModel, this.props.threadId]
        );
    },

    isPortalConversationSupportedThread() {
        return this.props.threadModel === "repair.order" && !!this.props.threadId;
    },

    isPortalConversationTabActive() {
        return (
            this.isPortalConversationSupportedThread() &&
            this.state.portalConversationTab === "portal_conversation"
        );
    },

    async loadPortalConversationData(force = false) {
        if (!this.isPortalConversationSupportedThread()) {
            this.state.portalConversation = null;
            return;
        }
        if (this.state.portalConversationLoading && !force) {
            return;
        }
        this.state.portalConversationLoading = true;
        try {
            this.state.portalConversation = await this.orm.call(
                "repair.order",
                "get_portal_repair_conversation_values",
                [[this.props.threadId]]
            );
        } finally {
            this.state.portalConversationLoading = false;
        }
    },

    async setPortalConversationTab(tabName) {
        this.state.portalConversationTab = tabName;
        if (tabName === "portal_conversation") {
            await this.loadPortalConversationData(true);
        }
    },

    onClickChatterTab() {
        this.setPortalConversationTab("chatter");
    },

    onClickPortalConversationTab() {
        this.setPortalConversationTab("portal_conversation");
    },

    get portalConversationMessageCount() {
        return this.state.portalConversation?.message_count || 0;
    },

    get portalConversationItems() {
        return this.state.portalConversation?.messages || [];
    },

    async openPortalConversationRecord() {
        if (!this.isPortalConversationSupportedThread()) {
            return;
        }
        const channelData = await this.orm.call(
            "repair.order",
            "action_open_portal_operator_chat",
            [[this.props.threadId]]
        );
        if (!channelData?.id) {
            return;
        }
        const thread = await this.store.Thread.getOrFetch(channelData);
        thread?.open();
    },
});
