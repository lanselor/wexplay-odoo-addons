/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Chatter } from "@mail/chatter/web_portal/chatter";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
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

        // En este Chatter, el documento real viene por props.threadModel/props.threadId
        const resModel = this.props.threadModel;
        const resId = this.props.threadId;

        if (!resModel || !resId) {
            return;
        }

        // Partner/company: no siempre están en props en backend.
        // En esta iteración 5B, precargamos modelo/id y dejamos partner para Iteración 6
        // (o lo resolveremos consultando el ORM con un mapping por modelo).
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
