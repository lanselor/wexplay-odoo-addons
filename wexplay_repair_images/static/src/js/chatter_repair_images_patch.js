/** @odoo-module **/

import { useEffect, useState } from "@odoo/owl";
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

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = this.orm || useService("orm");
        this.repairImagesState = useState({
            loading: false,
            uploading: false,
            values: null,
        });

        useEffect(
            () => {
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
                label: "Imágenes",
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

    get canManageRepairImages() {
        return Boolean(this.repairImagesState.values?.can_manage_images);
    },

    async onClickRepairImagesUpload() {
        if (!this.isRepairImagesSupportedThread() || this.repairImagesState.uploading) {
            return;
        }
        const input = document.createElement("input");
        input.type = "file";
        input.accept = "image/*";
        input.multiple = true;
        input.addEventListener("change", async () => {
            const files = Array.from(input.files || []).filter((file) =>
                (file.type || "").startsWith("image/")
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
                const binaryContent = await fileToBase64(file);
                await this.orm.call(
                    "repair.order",
                    "upload_repair_image_from_dropzone",
                    [[this.props.threadId], file.name, binaryContent]
                );
            }
            await this.loadRepairImagesData(true);
            this.notification.add("Imágenes subidas correctamente.", { type: "success" });
        } catch (error) {
            const message =
                error?.message ||
                error?.data?.message ||
                "No se pudo subir la imagen.";
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
            (file.type || "").startsWith("image/")
        );
        if (!files.length) {
            this.notification.add("Arrastra archivos de imagen válidos (JPG, PNG, WebP, GIF).", {
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
