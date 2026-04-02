/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ConsentRequestModal extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.state = useState({
            request: null,
            loading: true,
        });
        this.pollHandle = null;

        onMounted(async () => {
            await this.loadRequest();
            this.pollHandle = setInterval(() => this.loadRequest(), 2000);
        });

        onWillUnmount(() => {
            if (this.pollHandle) {
                clearInterval(this.pollHandle);
            }
        });
    }

    get stateLabel() {
        const labels = {
            queued: "En cola",
            presented: "Mostrada en kiosko",
            signed: "Firmada",
            cancelled: "Cancelada",
            failed: "Fallida",
        };
        return labels[this.state.request?.state] || this.state.request?.state || "";
    }

    async loadRequest() {
        const [request] = await this.orm.read(
            "wex.consent.request",
            [this.props.requestId],
            ["name", "state", "status_message", "document_id", "cancel_requested", "active_in_kiosk"]
        );
        this.state.request = request;
        this.state.loading = false;
    }

    async cancelRequest() {
        await this.orm.call("wex.consent.request", "action_cancel_request", [[this.props.requestId]]);
        await this.loadRequest();
        this.notification.add("Petición cancelada.", { type: "warning" });
    }

    async resendClean() {
        const action = await this.orm.call("wex.consent.request", "action_requeue_clean", [[this.props.requestId]]);
        this.notification.add("Se ha limpiado la firma y reenviado la petición.", { type: "info" });
        if (action?.type) {
            this.props.close();
            this.actionService.doAction(action);
            return;
        }
        await this.loadRequest();
    }

    async done() {
        this.props.close();
        await this.actionService.doAction({ type: "ir.actions.client", tag: "reload" });
    }

    close() {
        this.props.close();
    }
}

ConsentRequestModal.template = "wex_consent.ConsentRequestModal";
