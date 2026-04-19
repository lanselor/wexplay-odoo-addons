/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

let savedRange = null;
let toolbarObserver = null;
let panelRefreshPromise = null;
let panelBootObserver = null;

function parsePositiveId(value) {
    const id = Number(value);
    return Number.isInteger(id) && id > 0 ? id : null;
}

function getArticleIdFromHash() {
    const hash = window.location.hash || "";
    const params = new URLSearchParams(hash.startsWith("#") ? hash.slice(1) : hash);
    const model = params.get("model");
    const id = parsePositiveId(params.get("id"));
    if (model === "wex.knowledge.article" && id) {
        return id;
    }
    return null;
}

function getArticleIdFromPathname() {
    const pathname = window.location.pathname || "";
    const match = pathname.match(/\/wex\.knowledge\.article\/(\d+)(?:$|[/?#])/);
    return match ? parsePositiveId(match[1]) : null;
}

function getArticleIdFromDom() {
    const selectors = [
        ".o_form_view[data-res-id]",
        ".o_form_view .o_form_renderer[data-res-id]",
        ".o_form_view [data-res-id]",
        ".o_form_view input[name='id']",
        ".o_form_view .o_field_widget[name='id'] input",
    ];
    for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (!element) {
            continue;
        }
        const directId = parsePositiveId(element.dataset?.resId);
        if (directId) {
            return directId;
        }
        const valueId = parsePositiveId(element.value || element.getAttribute("value") || element.textContent);
        if (valueId) {
            return valueId;
        }
    }
    return null;
}

function getCurrentArticleId() {
    return getArticleIdFromHash() || getArticleIdFromPathname() || getArticleIdFromDom();
}

function getKnowledgeEditor() {
    return document.querySelector(".wex_kb_workspace_editor [contenteditable='true']");
}

function isRangeInsideEditor(range, editor) {
    if (!range || !editor) {
        return false;
    }
    const container = range.commonAncestorContainer;
    return editor === container || editor.contains(container);
}

function saveEditorSelection() {
    const editor = getKnowledgeEditor();
    const selection = window.getSelection();
    if (!editor || !selection || selection.rangeCount === 0) {
        return;
    }
    const range = selection.getRangeAt(0);
    if (isRangeInsideEditor(range, editor)) {
        savedRange = range.cloneRange();
    }
}

function restoreEditorSelection(editor) {
    const selection = window.getSelection();
    if (!editor || !selection) {
        return false;
    }
    if (savedRange && isRangeInsideEditor(savedRange, editor)) {
        selection.removeAllRanges();
        selection.addRange(savedRange);
        return true;
    }
    editor.focus();
    return false;
}

function insertHtmlAtCursor(editor, html) {
    const selectionRestored = restoreEditorSelection(editor);
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
        editor.insertAdjacentHTML("beforeend", html);
    } else {
        const range = selection.getRangeAt(0);
        if (!selectionRestored || !isRangeInsideEditor(range, editor)) {
            editor.insertAdjacentHTML("beforeend", html);
        } else {
            range.deleteContents();
            const template = document.createElement("template");
            template.innerHTML = html.trim();
            const fragment = template.content;
            const lastNode = fragment.lastChild;
            range.insertNode(fragment);
            if (lastNode) {
                range.setStartAfter(lastNode);
                range.setEndAfter(lastNode);
                selection.removeAllRanges();
                selection.addRange(range);
                savedRange = range.cloneRange();
            }
        }
    }
    editor.dispatchEvent(new Event("input", { bubbles: true }));
    editor.dispatchEvent(new Event("change", { bubbles: true }));
}

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function getEmbeddedImagesPanelElements() {
    const panel = document.querySelector(".wex_kb_embedded_images_panel");
    if (!panel) {
        return null;
    }
    return {
        panel,
        emptyState: document.querySelector(".wex_kb_embedded_images_empty"),
        table: panel.querySelector(".wex_kb_embedded_images_table"),
        body: panel.querySelector(".wex_kb_embedded_images_body"),
    };
}

function buildEmbeddedImagePanelRow(item) {
    const dmsUrl = `/web#id=${item.dms_file_id}&model=dms.file&view_type=form`;
    return `
        <div class="wex_kb_embedded_images_row" data-image-id="${item.id}">
            <div class="wex_kb_embedded_images_cell is-image">
                <img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.name)}"/>
            </div>
            <div class="wex_kb_embedded_images_cell">${escapeHtml(item.name)}</div>
            <div class="wex_kb_embedded_images_cell">${escapeHtml(item.uploaded_by_name || "")}</div>
            <div class="wex_kb_embedded_images_cell">${escapeHtml(item.uploaded_at || "")}</div>
            <div class="wex_kb_embedded_images_cell">${escapeHtml(item.dms_file_name || "")}</div>
            <div class="wex_kb_embedded_images_cell is-actions">
                <a href="${escapeHtml(dmsUrl)}" class="btn btn-link p-0" target="_self">DMS</a>
                <button type="button" class="btn btn-link p-0 text-danger wex_kb_delete_embedded_image" data-image-id="${item.id}">Eliminar</button>
            </div>
        </div>
    `.trim();
}

function renderEmbeddedImagesPanel(panelData) {
    const elements = getEmbeddedImagesPanelElements();
    if (!elements) {
        return;
    }
    const items = panelData?.items || [];
    if (elements.body) {
        elements.body.innerHTML = items.map(buildEmbeddedImagePanelRow).join("");
    }
    if (elements.emptyState) {
        elements.emptyState.style.display = items.length ? "none" : "";
    }
    if (elements.table) {
        elements.table.style.display = items.length ? "" : "none";
    }
}

async function refreshEmbeddedImagesPanel() {
    const articleId = getCurrentArticleId();
    const elements = getEmbeddedImagesPanelElements();
    if (!articleId || !elements || panelRefreshPromise) {
        return panelRefreshPromise;
    }
    panelRefreshPromise = rpc("/web/dataset/call_kw/wex.knowledge.article/get_embedded_image_panel_data", {
        model: "wex.knowledge.article",
        method: "get_embedded_image_panel_data",
        args: [[articleId]],
        kwargs: {},
    })
        .then((panelData) => {
            renderEmbeddedImagesPanel(panelData);
            return panelData;
        })
        .finally(() => {
            panelRefreshPromise = null;
        });
    return panelRefreshPromise;
}

function startEmbeddedImagesPanelBootObserver() {
    if (panelBootObserver || !document.body) {
        return;
    }
    panelBootObserver = new MutationObserver(() => {
        const articleId = getCurrentArticleId();
        const elements = getEmbeddedImagesPanelElements();
        if (!articleId || !elements) {
            return;
        }
        refreshEmbeddedImagesPanel();
    });
    panelBootObserver.observe(document.body, { childList: true, subtree: true });
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const result = String(reader.result || "");
            const base64 = result.includes(",") ? result.split(",").pop() : result;
            resolve(base64);
        };
        reader.onerror = () => reject(reader.error || new Error("File reading failed."));
        reader.readAsDataURL(file);
    });
}

async function uploadImageFromEditor(file) {
    const articleId = getCurrentArticleId();
    if (!articleId) {
        throw new Error("The article must be saved before inserting DMS images.");
    }
    const binaryContent = await fileToBase64(file);
    return rpc("/web/dataset/call_kw/wex.knowledge.article/upload_embedded_image_from_editor", {
        model: "wex.knowledge.article",
        method: "upload_embedded_image_from_editor",
        args: [[articleId], file.name, binaryContent],
        kwargs: {},
    });
}

async function openFilePickerAndInsert() {
    const editor = getKnowledgeEditor();
    if (!editor) {
        window.alert("No se ha encontrado el editor del articulo.");
        return;
    }

    saveEditorSelection();
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";

    input.addEventListener("change", async () => {
        const file = input.files && input.files[0];
        if (!file) {
            return;
        }
        await uploadDroppedOrSelectedFile(file);
    });

    input.click();
}

async function uploadDroppedOrSelectedFile(file) {
    const editor = getKnowledgeEditor();
    if (!editor) {
        window.alert("No se ha encontrado el editor del articulo.");
        return;
    }
    try {
        const payload = await uploadImageFromEditor(file);
        insertHtmlAtCursor(editor, payload.html);
        await refreshEmbeddedImagesPanel();
    } catch (error) {
        const message = error?.message || error?.data?.message || "No se pudo insertar la imagen.";
        window.alert(message);
    }
}

function matchesRestrictedToolbarLabel(element) {
    const rawLabel = [
        element.getAttribute("title"),
        element.getAttribute("aria-label"),
        element.textContent,
    ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
    return [
        "media",
        "image",
        "imagen",
        "replace",
        "upload file",
        "subir archivo",
    ].some((keyword) => rawLabel.includes(keyword));
}

function hideNativeMediaOptions() {
    const articleForm = document.querySelector(".wex_kb_article_form");
    if (!articleForm) {
        return;
    }
    const restrictedElements = document.querySelectorAll("button, a, .dropdown-item, .o-dropdown-item");
    for (const element of restrictedElements) {
        const toolbarLikeContainer = element.closest(
            ".o-we-toolbar, .o-we-toolbar-container, .o_we_toolbar, .oe-toolbar, .o_popover, .popover, .o-dropdown--menu, .dropdown-menu"
        );
        if (!toolbarLikeContainer) {
            continue;
        }
        if (matchesRestrictedToolbarLabel(element)) {
            element.style.display = "none";
        }
    }
}

function startToolbarObserver() {
    if (toolbarObserver) {
        return;
    }
    if (!document.body) {
        return;
    }
    toolbarObserver = new MutationObserver(() => {
        hideNativeMediaOptions();
    });
    toolbarObserver.observe(document.body, { childList: true, subtree: true });
    hideNativeMediaOptions();
}

document.addEventListener("selectionchange", () => {
    saveEditorSelection();
});

document.addEventListener("click", (ev) => {
    const button = ev.target.closest(".wex_kb_insert_dms_image");
    if (!button) {
        const deleteButton = ev.target.closest(".wex_kb_delete_embedded_image");
        if (deleteButton) {
            ev.preventDefault();
            const articleId = getCurrentArticleId();
            const imageId = parsePositiveId(deleteButton.dataset.imageId);
            if (!articleId || !imageId) {
                window.alert("No se ha podido identificar la imagen a eliminar.");
                return;
            }
            rpc("/web/dataset/call_kw/wex.knowledge.article/delete_embedded_image_from_panel", {
                model: "wex.knowledge.article",
                method: "delete_embedded_image_from_panel",
                args: [[articleId], imageId],
                kwargs: {},
            })
                .then((panelData) => {
                    renderEmbeddedImagesPanel(panelData);
                })
                .catch((error) => {
                    const message = error?.message || error?.data?.message || "No se pudo eliminar la imagen.";
                    window.alert(message);
                });
            return;
        }
        const dropzone = ev.target.closest(".wex_kb_embedded_dropzone");
        if (!dropzone) {
            return;
        }
        ev.preventDefault();
        openFilePickerAndInsert();
        return;
    }
    ev.preventDefault();
    ev.stopPropagation();
    openFilePickerAndInsert();
});

document.addEventListener("dragover", (ev) => {
    const dropzone = ev.target.closest(".wex_kb_embedded_dropzone");
    if (!dropzone) {
        return;
    }
    ev.preventDefault();
    dropzone.classList.add("is-dragover");
});

document.addEventListener("dragleave", (ev) => {
    const dropzone = ev.target.closest(".wex_kb_embedded_dropzone");
    if (!dropzone) {
        return;
    }
    dropzone.classList.remove("is-dragover");
});

document.addEventListener("drop", (ev) => {
    const dropzone = ev.target.closest(".wex_kb_embedded_dropzone");
    if (!dropzone) {
        return;
    }
    ev.preventDefault();
    dropzone.classList.remove("is-dragover");
    const files = Array.from(ev.dataTransfer?.files || []);
    const imageFile = files.find((file) => (file.type || "").startsWith("image/"));
    if (!imageFile) {
        window.alert("Arrastra un archivo de imagen valido.");
        return;
    }
    uploadDroppedOrSelectedFile(imageFile);
});

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        startToolbarObserver();
        startEmbeddedImagesPanelBootObserver();
        refreshEmbeddedImagesPanel();
    });
} else {
    startToolbarObserver();
    startEmbeddedImagesPanelBootObserver();
    refreshEmbeddedImagesPanel();
}
