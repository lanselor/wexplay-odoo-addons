/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Chatter } from "@mail/chatter/web_portal/chatter";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.actionService = useService("action");
    },

    onClickWhatsApp() {
        const resModel = this.props.threadModel;
        const resId = this.props.threadId;
        if (!resModel || !resId) {
            return;
        }

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "whatsapp.compose.wizard",
            view_mode: "form",
            target: "new",
            context: {
                default_res_model: resModel,
                default_res_id: resId,
            },
        });
    },
});
