/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Chatter } from "@mail/chatter/web/chatter";

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.userService = useService("user");
    },

    async onClickWhatsApp() {
        const hasGroup = await this.userService.hasGroup(
            "wex_whatsapp_chatter.group_whatsapp_user"
        );
        if (!hasGroup) {
            return;
        }

        const record = this.props.record;
        if (!record) {
            return;
        }

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "whatsapp.compose.wizard",
            view_mode: "form",
            target: "new",
            context: {
                default_res_model: record.resModel,
                default_res_id: record.resId,
                default_company_id: record.data.company_id?.[0],
                default_partner_id: record.data.partner_id?.[0],
            },
        });
    },
});
