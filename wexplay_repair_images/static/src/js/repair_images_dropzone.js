/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

function parsePositiveId(value) {
    const id = Number(value);
    return Number.isInteger(id) && id > 0 ? id : null;
}

function getRepairOrderId() {
    // Odoo 18 usa rutas tipo /odoo/repairs/653
    const match = window.location.pathname.match(/\/repairs\/(\d+)(?:$|[/?#])/);
    return match ? parsePositiveId(match[1]) : null;
}

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

function setDropzoneLoading(dropzone, loading) {
    if (loading) {
        dropzone.classList.add("is-loading");
        dropzone.setAttribute("aria-busy", "true");
    } else {
        dropzone.classList.remove("is-loading");
        dropzone.removeAttribute("aria-busy");
    }
}

async function reloadFormRecord() {
    const formEl = document.querySelector(".o_form_view");
    let node = formEl && formEl.__owl__;
    while (node) {
        const comp = node.component;
        if (comp && comp.model && typeof comp.model.load === "function") {
            await comp.model.load();
            return;
        }
        node = node.parent;
    }
    window.location.reload();
}

async function uploadImagesToRepairOrder(repairId, files, dropzone) {
    setDropzoneLoading(dropzone, true);
    try {
        for (const file of files) {
            const binaryContent = await fileToBase64(file);
            await rpc("/web/dataset/call_kw/repair.order/upload_repair_image_from_dropzone", {
                model: "repair.order",
                method: "upload_repair_image_from_dropzone",
                args: [[repairId], file.name, binaryContent],
                kwargs: {},
            });
        }
        await reloadFormRecord();
    } catch (error) {
        setDropzoneLoading(dropzone, false);
        const message = (error && (error.message || (error.data && error.data.message))) || "No se pudo subir la imagen.";
        window.alert(message);
    }
}

function filterImageFiles(files) {
    return Array.from(files || []).filter((file) => (file.type || "").startsWith("image/"));
}

function openFilePickerAndUpload(dropzone) {
    const repairId = getRepairOrderId();
    if (!repairId) {
        window.alert("Guarda la orden de reparación antes de subir imágenes.");
        return;
    }
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.multiple = true;
    input.addEventListener("change", () => {
        const files = filterImageFiles(input.files);
        if (!files.length) {
            return;
        }
        uploadImagesToRepairOrder(repairId, files, dropzone);
    });
    input.click();
}

document.addEventListener("click", (ev) => {
    const dropzone = ev.target.closest(".wex_repair_images_dropzone");
    if (!dropzone) {
        return;
    }
    ev.preventDefault();
    openFilePickerAndUpload(dropzone);
});

document.addEventListener("keydown", (ev) => {
    if (ev.key !== "Enter" && ev.key !== " ") {
        return;
    }
    const dropzone = ev.target.closest(".wex_repair_images_dropzone");
    if (!dropzone) {
        return;
    }
    ev.preventDefault();
    openFilePickerAndUpload(dropzone);
});

document.addEventListener("dragover", (ev) => {
    const dropzone = ev.target.closest(".wex_repair_images_dropzone");
    if (!dropzone) {
        return;
    }
    ev.preventDefault();
    dropzone.classList.add("is-dragover");
});

document.addEventListener("dragleave", (ev) => {
    const dropzone = ev.target.closest(".wex_repair_images_dropzone");
    if (!dropzone) {
        return;
    }
    if (dropzone.contains(ev.relatedTarget)) {
        return;
    }
    dropzone.classList.remove("is-dragover");
});

document.addEventListener("drop", (ev) => {
    const dropzone = ev.target.closest(".wex_repair_images_dropzone");
    if (!dropzone) {
        return;
    }
    ev.preventDefault();
    dropzone.classList.remove("is-dragover");
    const repairId = getRepairOrderId();
    if (!repairId) {
        window.alert("Guarda la orden de reparación antes de subir imágenes.");
        return;
    }
    const files = filterImageFiles(ev.dataTransfer && ev.dataTransfer.files);
    if (!files.length) {
        window.alert("Arrastra archivos de imagen válidos (JPG, PNG, WebP, GIF).");
        return;
    }
    uploadImagesToRepairOrder(repairId, files, dropzone);
});
