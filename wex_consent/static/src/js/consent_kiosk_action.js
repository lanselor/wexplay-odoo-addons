/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { ConsentRequestModal } from "./consent_request_modal";

export class ConsentKioskAction extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.canvasRef = useRef("signatureCanvas");
        this.state = useState({
            request: null,
            document: null,
            signerName: "",
            signerVat: "",
            confirmationOk: true,
            legalDataProtection: true,
            allowEmailAll: true,
            allowWhatsappAll: true,
            warrantyConditionsAccepted: true,
            loading: true,
            drawing: false,
            sessionId: this.props.action?.params?.sessionId || null,
        });
        this.pollHandle = null;

        onMounted(async () => {
            document.body.classList.add("wex_consent_kiosk_mode");
            await this.pollNextRequest();
            this.pollHandle = setInterval(() => this.pollNextRequest(), 2500);
        });

        onWillUnmount(() => {
            document.body.classList.remove("wex_consent_kiosk_mode");
            if (this.pollHandle) {
                clearInterval(this.pollHandle);
            }
        });
    }

    get sessionId() {
        return this.state.sessionId;
    }

    get documentTypeLabel() {
        const labels = {
            reception: "Recepcion",
            delivery: "Entrega",
        };
        return labels[this.state.document?.document_type] || this.state.document?.document_type || "";
    }

    get documentAccessories() {
        if (this.state.document?.accessories) {
            return this.state.document.accessories;
        }
        if (!this.state.document?.snapshot_json) {
            return "";
        }
        try {
            const snapshot = JSON.parse(this.state.document.snapshot_json);
            return snapshot.accessories || "";
        } catch {
            return "";
        }
    }

    async pollNextRequest() {
        if (!this.state.sessionId) {
            this.state.sessionId = await this.orm.call(
                "wex.consent.kiosk.session",
                "get_default_session_id",
                []
            );
        }

        if (this.state.request?.id) {
            const [currentRequest] = await this.orm.read(
                "wex.consent.request",
                [this.state.request.id],
                ["state", "status_message"]
            );
            if (currentRequest.state !== "presented") {
                this.state.request = null;
                this.state.document = null;
                this.state.loading = false;
            } else {
                return;
            }
        }

        const requestId = await this.orm.call(
            "wex.consent.document",
            "kiosk_pull_next_request",
            [this.sessionId]
        );
        if (!requestId) {
            this.state.loading = false;
            return;
        }

        const [request] = await this.orm.read(
            "wex.consent.request",
            [requestId],
            ["id", "name", "document_id", "document_type", "repair_order_id"]
        );
        const [document] = await this.orm.read(
            "wex.consent.document",
            [request.document_id[0]],
            [
                "id",
                "name",
                "document_type",
                "issue_description",
                "device_description",
                "accessories",
                "snapshot_json",
                "repair_notes",
                "customer_review_statement",
                "signer_name",
                "signer_vat",
                "legal_text",
                "legal_data_protection",
                "allow_email_non_commercial",
                "allow_email_commercial",
                "allow_whatsapp_non_commercial",
                "allow_whatsapp_commercial",
                "warranty_conditions_accepted",
            ]
        );

        this.state.request = request;
        this.state.document = document;
        this.restoreDocumentDefaults();
        this.state.loading = false;
        setTimeout(() => this.resetCanvas(), 0);
    }

    restoreDocumentDefaults() {
        this.state.signerName = this.state.document?.signer_name || "";
        this.state.signerVat = this.state.document?.signer_vat || "";
        this.state.confirmationOk = true;
        this.state.legalDataProtection = !!this.state.document?.legal_data_protection;
        this.state.allowEmailAll = Boolean(
            this.state.document?.allow_email_non_commercial
            || this.state.document?.allow_email_commercial
        );
        this.state.allowWhatsappAll = Boolean(
            this.state.document?.allow_whatsapp_non_commercial
            || this.state.document?.allow_whatsapp_commercial
        );
        this.state.warrantyConditionsAccepted = !!this.state.document?.warranty_conditions_accepted;
    }

    resetCanvas() {
        const canvas = this.canvasRef.el;
        if (!canvas) {
            return;
        }
        const context = canvas.getContext("2d");
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, canvas.width, canvas.height);
        context.strokeStyle = "#1f2937";
        context.lineWidth = 2;
        context.lineCap = "round";
        context.lineJoin = "round";
    }

    getPoint(event) {
        const canvas = this.canvasRef.el;
        const rect = canvas.getBoundingClientRect();
        const source = event.touches ? event.touches[0] : event;
        return {
            x: source.clientX - rect.left,
            y: source.clientY - rect.top,
        };
    }

    startDrawing(event) {
        const canvas = this.canvasRef.el;
        if (!canvas) {
            return;
        }
        const context = canvas.getContext("2d");
        const point = this.getPoint(event);
        context.beginPath();
        context.moveTo(point.x, point.y);
        this.state.drawing = true;
        event.preventDefault();
    }

    draw(event) {
        if (!this.state.drawing) {
            return;
        }
        const canvas = this.canvasRef.el;
        const context = canvas.getContext("2d");
        const point = this.getPoint(event);
        context.lineTo(point.x, point.y);
        context.stroke();
        event.preventDefault();
    }

    stopDrawing(event) {
        if (!this.state.drawing) {
            return;
        }
        this.state.drawing = false;
        event.preventDefault();
    }

    clearSignature() {
        this.restoreDocumentDefaults();
        this.resetCanvas();
    }

    async cancelRequest() {
        if (!this.state.request?.id) {
            return;
        }
        await this.orm.call("wex.consent.request", "action_cancel_from_kiosk", [[this.state.request.id]]);
        this.notification.add("Firma cancelada desde el kiosko.", { type: "warning" });
        this.state.request = null;
        this.state.document = null;
        this.state.loading = false;
        await this.pollNextRequest();
    }

    async submitSignature() {
        if (!this.state.signerName.trim()) {
            this.notification.add("El nombre del firmante es obligatorio.", { type: "danger" });
            return;
        }
        if (!this.state.signerVat.trim()) {
            this.notification.add("El DNI/NIF del firmante es obligatorio.", { type: "danger" });
            return;
        }

        const canvas = this.canvasRef.el;
        const signatureImage = canvas.toDataURL("image/png").split(",")[1];
        if (!signatureImage) {
            this.notification.add("La firma esta vacia.", { type: "danger" });
            return;
        }

        const consentValues = this.state.document?.document_type === "reception"
            ? {
                legal_data_protection: this.state.legalDataProtection,
                allow_email_non_commercial: this.state.allowEmailAll,
                allow_email_commercial: this.state.allowEmailAll,
                allow_whatsapp_non_commercial: this.state.allowWhatsappAll,
                allow_whatsapp_commercial: this.state.allowWhatsappAll,
                warranty_conditions_accepted: this.state.warrantyConditionsAccepted,
            }
            : {};

        await this.orm.call(
            "wex.consent.request",
            "action_sign_request",
            [[this.state.request.id], this.state.signerName, signatureImage, this.state.confirmationOk, this.state.signerVat, consentValues]
        );
        this.notification.add("Firma completada.", { type: "success" });
        this.state.request = null;
        this.state.document = null;
        this.state.loading = false;
        await this.pollNextRequest();
    }
}

ConsentKioskAction.template = "wex_consent.ConsentKioskAction";

const actionsRegistry = registry.category("actions");

if (!actionsRegistry.contains("wex_consent.open_kiosk")) {
    actionsRegistry.add("wex_consent.open_kiosk", ConsentKioskAction);
}

if (!actionsRegistry.contains("wex_consent.open_signature_request")) {
    actionsRegistry.add("wex_consent.open_signature_request", async (env, action) => {
        env.services.dialog.add(ConsentRequestModal, {
            requestId: action?.params?.requestId,
        });
    });
}
