/** @odoo-module **/
/**
 * Wex WhatsApp Chatter - Chatter button handler (Odoo 18)
 *
 * Objetivo:
 * - Añadir comportamiento al botón "WhatsApp" insertado por QWeb (template OWL mail.Chatter)
 * - Abrir el wizard `whatsapp.compose.wizard` como modal, precargando el documento activo.
 *
 * Notas críticas:
 * - NO usamos `useService("user")`: en algunos contextos del chatter puede no estar disponible y rompe OWL.
 * - Solo usamos `action` service para lanzar el wizard.
 * - `threadModel` y `threadId` son las fuentes más estables del documento actual en este Chatter.
 */

console.warn("WEX_WHATSAPP_CHATTER: loaded Version 10");

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { Chatter } from "@mail/chatter/web_portal/chatter";

patch(Chatter.prototype, {
    setup() {
        // Mantener la inicialización estándar del chatter
        super.setup(...arguments);

        // Servicio necesario para abrir acciones (wizard modal)
        this.actionService = useService("action");
    },

    /**
     * Handler del botón WhatsApp.
     * Abre el wizard con el contexto del documento actual para que el servidor
     * pueda precargar partner/company y filtrar plantillas correctamente.
     */
    onClickWhatsApp() {
        const resModel = this.props.threadModel;
        const resId = this.props.threadId;

        // Si no hay documento (por ejemplo, formulario aún no guardado), no hacemos nada
        if (!resModel || !resId) {
            return;
        }

        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "whatsapp.compose.wizard",
            view_mode: "form",
            target: "new",
            context: {
                // Claves estándar para default_get / defaults en TransientModel
                default_res_model: resModel,
                default_res_id: resId,
            },
        });
    },
});
