/** @odoo-module **/

import { useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/chatter/web_portal/chatter";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        Object.assign(this.state, {
            wexChatterFooterTab: this.state.wexChatterFooterTab || "chatter",
        });

        useEffect(
            () => {
                this.state.wexChatterFooterTab = "chatter";
            },
            () => [this.props.threadModel, this.props.threadId]
        );
    },

    isWexChatterFooterEnabled() {
        return Boolean(this.props.threadModel && this.props.threadId);
    },

    getWexChatterFooterTabs() {
        return [
            {
                name: "chatter",
                label: "Chatter",
                count: 0,
            },
        ];
    },

    isWexChatterFooterTabActive(tabName) {
        return this.state.wexChatterFooterTab === tabName;
    },

    isWexChatterMainTabActive() {
        return this.isWexChatterFooterTabActive("chatter");
    },

    async _wexOnChatterFooterTabChanged() {},

    async setWexChatterFooterTab(tabName) {
        this.state.wexChatterFooterTab = tabName;
        await this._wexOnChatterFooterTabChanged(tabName);
    },

    async onClickWexChatterFooterTab(event) {
        const tabName = event.currentTarget.dataset.tabName;
        if (!tabName) {
            return;
        }
        await this.setWexChatterFooterTab(tabName);
    },
});
