/** @odoo-module **/

import { Component, onWillUnmount, useEffect, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/chatter/web_portal/chatter";

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const result = String(reader.result || "");
            const base64 = result.includes(",") ? result.split(",").pop() : result;
            resolve(base64);
        };
        reader.onerror = () => reject(reader.error || new Error("Error leyendo el archivo."));
        reader.readAsDataURL(file);
    });
}

function isVideoFile(file) {
    const extension = (file.name || "").split(".").pop().toLowerCase();
    return ["mp4", "mov", "webm", "mkv"].includes(extension) || (file.type || "").startsWith("video/");
}

function uploadVideoFile(repairId, file) {
    return new Promise((resolve, reject) => {
        const request = new XMLHttpRequest();
        const data = new FormData();
        data.append("csrf_token", odoo.csrf_token);
        data.append("repair_id", repairId);
        data.append("ufile", file);
        request.open("POST", "/wexplay/repair/media/upload");
        request.addEventListener("load", () => {
            let response = {};
            try {
                response = JSON.parse(request.responseText || "{}");
            } catch {
                reject(new Error("La respuesta de subida no es válida."));
                return;
            }
            if (request.status < 200 || request.status >= 300 || response.error) {
                reject(new Error(response.error || "No se pudo subir el vídeo."));
                return;
            }
            resolve(response);
        });
        request.addEventListener("error", () => reject(new Error("No se pudo subir el vídeo.")));
        request.send(data);
    });
}

class RepairImageViewerDialog extends Component {
    close() {
        this.props.close();
    }
}

RepairImageViewerDialog.components = { Dialog };
RepairImageViewerDialog.template = "wexplay_repair_images.RepairImageViewerDialog";
RepairImageViewerDialog.props = {
    image: Object,
    close: Function,
};

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = this.orm || useService("orm");
        this.repairImagesState = useState({
            loading: false,
            uploading: false,
            values: null,
        });
        this.repairMediaJobsState = useState({ items: [] });
        this.repairMediaJobsPollTimeout = null;
        this.repairMediaJobsPollingActive = true;

        onWillUnmount(() => {
            this.repairMediaJobsPollingActive = false;
            window.clearTimeout(this.repairMediaJobsPollTimeout);
        });

        useEffect(
            () => {
                window.clearTimeout(this.repairMediaJobsPollTimeout);
                this.repairMediaJobsState.items = [];
                this.repairImagesState.values = null;
                if (this.isRepairImagesSupportedThread()) {
                    this.loadRepairImagesData();
                }
            },
            () => [this.props.threadModel, this.props.threadId]
        );
    },

    isRepairImagesSupportedThread() {
        return this.props.threadModel === "repair.order" && !!this.props.threadId;
    },

    isRepairImagesTabActive() {
        return this.isRepairImagesSupportedThread() && this.isWexChatterFooterTabActive("repair_images");
    },

    getWexChatterFooterTabs() {
        const tabs = super.getWexChatterFooterTabs(...arguments);
        if (!this.isRepairImagesSupportedThread()) {
            return tabs;
        }
        return [
            ...tabs,
            {
                name: "repair_images",
                label: "Multimedia",
                count: this.repairImagesCount,
            },
        ];
    },

    async _wexOnChatterFooterTabChanged(tabName) {
        await super._wexOnChatterFooterTabChanged(...arguments);
        if (tabName === "repair_images") {
            await this.loadRepairImagesData(true);
        }
    },

    async loadRepairImagesData(force = false) {
        if (!this.isRepairImagesSupportedThread()) {
            this.repairImagesState.values = null;
            return;
        }
        if (this.repairImagesState.loading && !force) {
            return;
        }
        this.repairImagesState.loading = true;
        try {
            this.repairImagesState.values = await this.orm.call(
                "repair.order",
                "get_repair_images_chatter_values",
                [[this.props.threadId]]
            );
            this.repairMediaJobsState.items = this.repairImagesState.values.jobs || [];
            this.scheduleRepairMediaJobsPolling();
        } finally {
            this.repairImagesState.loading = false;
        }
    },

    get repairImagesCount() {
        return this.repairImagesState.values?.count || 0;
    },

    get repairImagesItems() {
        return this.repairImagesState.values?.images || [];
    },

    get repairMediaJobs() {
        return this.repairMediaJobsState.items;
    },

    scheduleRepairMediaJobsPolling() {
        window.clearTimeout(this.repairMediaJobsPollTimeout);
        if (
            !this.repairMediaJobsPollingActive ||
            !this.repairMediaJobs.some((job) => ["queued", "processing"].includes(job.state))
        ) {
            return;
        }
        const repairId = this.props.threadId;
        this.repairMediaJobsPollTimeout = window.setTimeout(
            () => this.loadRepairMediaJobs(repairId),
            30000
        );
    },

    async loadRepairMediaJobs(repairId = this.props.threadId) {
        if (
            !this.repairMediaJobsPollingActive ||
            !this.isRepairImagesSupportedThread() ||
            this.props.threadId !== repairId
        ) {
            return;
        }
        const hadPendingJobs = this.repairMediaJobs.some((job) =>
            ["queued", "processing"].includes(job.state)
        );
        let jobs;
        try {
            jobs = await this.orm.call(
                "repair.order",
                "get_repair_media_job_values",
                [[repairId]]
            );
        } catch (error) {
            // El chatter puede desmontarse mientras la RPC de sondeo sigue en vuelo.
            if (this.repairMediaJobsPollingActive && this.props.threadId === repairId) {
                this.scheduleRepairMediaJobsPolling();
            }
            return;
        }
        if (
            !this.repairMediaJobsPollingActive ||
            !this.isRepairImagesSupportedThread() ||
            this.props.threadId !== repairId
        ) {
            return;
        }
        this.repairMediaJobsState.items = jobs;
        const hasPendingJobs = jobs.some((job) => ["queued", "processing"].includes(job.state));
        if (hadPendingJobs && !hasPendingJobs) {
            try {
                await this.loadRepairImagesData(true);
            } catch {
                // El refresco completo también puede terminar tras cerrar el chatter.
            }
            return;
        }
        this.scheduleRepairMediaJobsPolling();
    },

    get canManageRepairImages() {
        return Boolean(this.repairImagesState.values?.can_manage_images);
    },

    async onClickRepairImagesUpload() {
        if (!this.isRepairImagesSupportedThread() || this.repairImagesState.uploading) {
            return;
        }
        const input = document.createElement("input");
        input.type = "file";
        input.accept = "image/*,video/mp4,video/quicktime,video/webm,video/x-matroska,.mkv";
        input.multiple = true;
        input.addEventListener("change", async () => {
            const files = Array.from(input.files || []).filter((file) =>
                (file.type || "").startsWith("image/") || isVideoFile(file)
            );
            if (!files.length) {
                return;
            }
            await this.uploadRepairImages(files);
        });
        input.click();
    },

    async uploadRepairImages(files) {
        this.repairImagesState.uploading = true;
        try {
            for (const file of files) {
                if (isVideoFile(file)) {
                    await uploadVideoFile(this.props.threadId, file);
                    continue;
                }
                const binaryContent = await fileToBase64(file);
                await this.orm.call("repair.order", "upload_repair_image_from_dropzone", [[this.props.threadId], file.name, binaryContent]);
            }
            await this.loadRepairImagesData(true);
            this.notification.add("Archivos subidos correctamente.", { type: "success" });
        } catch (error) {
            const message =
                error?.message ||
                error?.data?.message ||
                "No se pudo subir el archivo.";
            this.notification.add(message, { type: "danger" });
        } finally {
            this.repairImagesState.uploading = false;
        }
    },

    onRepairImagesDragOver(event) {
        event.preventDefault();
        event.currentTarget.classList.add("is-dragover");
    },

    onRepairImagesDragLeave(event) {
        if (event.currentTarget.contains(event.relatedTarget)) {
            return;
        }
        event.currentTarget.classList.remove("is-dragover");
    },

    async onRepairImagesDrop(event) {
        event.preventDefault();
        event.currentTarget.classList.remove("is-dragover");
        const files = Array.from(event.dataTransfer?.files || []).filter((file) =>
            (file.type || "").startsWith("image/") || isVideoFile(file)
        );
        if (!files.length) {
            this.notification.add("Arrastra imágenes o vídeos válidos.", {
                type: "warning",
            });
            return;
        }
        await this.uploadRepairImages(files);
    },

    onRepairImagesDropzoneKeydown(event) {
        if (event.key !== "Enter" && event.key !== " ") {
            return;
        }
        event.preventDefault();
        this.onClickRepairImagesUpload();
    },

    async onClickRepairImagePreviewButton(event) {
        const imageId = Number(event.currentTarget.dataset.imageId || 0);
        if (!imageId) {
            return;
        }
        await this.onClickRepairImagePreview(imageId);
    },

    onClickRepairImageViewerButton(event) {
        const imageId = Number(event.currentTarget.dataset.imageId || 0);
        const image = this.repairImagesItems.find((item) => item.id === imageId);
        if (!image?.preview_url) {
            return;
        }
        this.openRepairImageViewer(image);
    },

    openRepairImageViewer(image) {
        this.dialog.add(RepairImageViewerDialog, { image });
    },

    async onClickRepairVideoJobRetry(event) {
        const jobId = Number(event.currentTarget.dataset.jobId || 0);
        if (!jobId) {
            return;
        }
        await this.orm.call("repair.order", "action_requeue_repair_video_job", [[this.props.threadId], jobId]);
        await this.loadRepairImagesData(true);
    },

    async onClickRepairVideoJobCancel(event) {
        const jobId = Number(event.currentTarget.dataset.jobId || 0);
        if (!jobId) {
            return;
        }
        await this.orm.call("repair.order", "action_cancel_repair_video_job", [[this.props.threadId], jobId]);
        await this.loadRepairImagesData(true);
    },

    async onClickRepairImageDmsFileButton(event) {
        const imageId = Number(event.currentTarget.dataset.imageId || 0);
        if (!imageId) {
            return;
        }
        await this.onClickRepairImageDmsFile(imageId);
    },

    async onClickRepairImageSatReportToggleButton(event) {
        const imageId = Number(event.currentTarget.dataset.imageId || 0);
        if (!imageId) {
            return;
        }
        await this.onClickRepairImageSatReportToggle(imageId);
    },

    async onClickRepairImagePreview(imageId) {
        const action = await this.orm.call(
            "repair.order",
            "action_open_repair_image_preview",
            [[this.props.threadId], imageId]
        );
        await this.action.doAction(action);
        await this.loadRepairImagesData(true);
    },

    async onClickRepairImageDmsFile(imageId) {
        const action = await this.orm.call(
            "repair.order",
            "action_open_repair_image_dms_file",
            [[this.props.threadId], imageId]
        );
        await this.action.doAction(action);
    },

    async onClickRepairImageSatReportToggle(imageId) {
        await this.orm.call(
            "repair.order",
            "action_toggle_repair_image_sat_report",
            [[this.props.threadId], imageId]
        );
        await this.loadRepairImagesData(true);
    },
});
