/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Chatter } from "@mail/core/web/chatter"; // Ruta corregida para Odoo 18

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.userService = useService("user");
    },

    async onClickWhatsApp() {
        // 1. Verificación de seguridad
        const hasGroup = await this.userService.hasGroup(
            "wex_whatsapp_chatter.group_whatsapp_user"
        );

        if (!hasGroup) {
            return;
        }

        // 2. En Odoo 18, la información reside en el thread
        const thread = this.props.thread;
        if (!thread) {
            return;
        }

        // 3. Obtener el registro actual para extraer partner_id o company_id
        // Nota: Accedemos a model.env para buscar el registro si es necesario, 
        // pero lo más seguro es usar los datos del thread.
        
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "whatsapp.compose.wizard",
            view_mode: "form",
            target: "new",
            context: {
                default_res_model: thread.model,
                default_res_id: thread.id,
                // En el chatter, partner_id suele obtenerse del registro cargado en la vista
                default_partner_id: this.props.thread.partner?.id, 
            },
        });
    },
});