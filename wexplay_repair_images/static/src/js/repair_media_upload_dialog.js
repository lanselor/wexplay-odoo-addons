/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { loadJS } from "@web/core/assets";

class RepairMediaDialog extends Dialog {
    static props = { ...Dialog.props, busy: { type: Boolean, optional: true } };

    async dismiss() {
        if (!this.props.busy) return super.dismiss();
    }
}

export class RepairMediaUploadDialog extends Component {
    static template = "wexplay_repair_images.RepairMediaUploadDialog";
    static components = { Dialog: RepairMediaDialog };
    static props = { files: Array, uploadFile: Function, onUploaded: Function, close: Function };

    setup() {
        this.items = this.props.files.map((file, id) => ({
            id, file, description: "", url: URL.createObjectURL(file),
            video: file.type.startsWith("video/") || /\.(mp4|mov|webm|mkv)$/i.test(file.name),
            previewUrl: null, design: null, edited: null, dirty: false, uploaded: false,
        }));
        this.state = useState({ index: 0, busy: false, ready: false, error: "", completed: 0, revision: 0 });
        this.editorRef = useRef("editor");
        this.alive = true;
        onMounted(async () => {
            try {
                await loadJS("/wexplay_repair_images/static/lib/filerobot/filerobot-image-editor-4.8.1.min.js?wex=3");
                if (this.alive) {
                    this.state.ready = true;
                    this.scheduleEditorMount();
                }
            } catch {
                if (this.alive) this.state.error = "No se pudo cargar el editor. Cierra la ventana e inténtalo de nuevo.";
            }
        });
        onWillUnmount(() => {
            this.alive = false;
            cancelAnimationFrame(this.editorMountFrame);
            this.destroyEditor();
            this.items.forEach((item) => {
                URL.revokeObjectURL(item.url);
                if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
            });
        });
    }

    get current() { return this.items[this.state.index]; }
    get pending() { return this.items.filter((item) => !item.uploaded); }

    destroyEditor() {
        this.editor?.terminate();
        this.editor = null;
    }

    scheduleEditorMount() {
        cancelAnimationFrame(this.editorMountFrame);
        this.editorMountFrame = requestAnimationFrame(() => {
            this.editorMountFrame = requestAnimationFrame(() => {
                if (this.alive) this.mountEditor();
            });
        });
    }

    mountEditor() {
        this.destroyEditor();
        const item = this.current;
        if (!item || item.video || !this.state.ready) return;
        const Editor = window.FilerobotImageEditor;
        this.editor = new Editor(this.editorRef.el, {
            source: item.url,
            loadableDesignState: item.design,
            tabsIds: [Editor.TABS.ADJUST, Editor.TABS.ANNOTATE],
            defaultTabId: Editor.TABS.ADJUST,
            defaultToolId: Editor.TOOLS.CROP,
            Crop: { noPresets: true },
            Pen: { strokeWidth: 4, opacity: 1, shadowBlur: 0, shadowOpacity: 0, selectAnnotationAfterDrawing: false },
            annotationsCommon: { stroke: "#ff0000", fill: "#ff0000", opacity: 1, shadowBlur: 0, shadowOpacity: 0 },
            removeSaveButton: true,
            useBackendTranslations: false,
            useCloudimage: false,
            avoidChangesNotSavedAlertOnLeave: true,
            // El diálogo fija la altura; observar su contenido puede realimentar el layout.
            observePluginContainerSize: false,
            previewPixelRatio: 1,
            theme: { typography: { fontFamily: "Arial, sans-serif" } },
            onModify: (design) => { item.design = design; item.dirty = true; },
            translations: {
                adjustTab: "Recortar", annotateTabLabel: "Pintar", cropTool: "Recortar",
                penTool: "Pincel", apply: "Aplicar", cancel: "Cancelar", confirm: "Confirmar",
                loading: "Cargando…", invalidImageError: "El navegador no puede abrir esta imagen.",
                resetOperations: "Restablecer imagen", undoTitle: "Deshacer", redoTitle: "Rehacer",
                changesLoseWarningHint: "¿Quieres restablecer la imagen y eliminar sus cambios?",
                warning: "Aviso", original: "Original", custom: "Libre", size: "Grosor",
                stroke: "Trazo", opacity: "Opacidad", color: "Color", colors: "Colores",
                showImageTitle: "Ver original", zoomInTitle: "Acercar", zoomOutTitle: "Alejar",
                fitSize: "Ajustar a la pantalla", actualSize: "Tamaño real", tabsMenu: "Herramientas",
                mutualizedFailedToLoadImg: "No se pudo abrir la imagen. Puedes subir el archivo sin editar.",
            },
        });
        this.editor.render();
    }

    async captureCurrentImage() {
        const item = this.current;
        if (!this.editor || !item.dirty || item.uploaded) return;
        const result = this.editor.getCurrentImgData({ extension: "png" });
        if (!result?.imageData?.imageCanvas) throw new Error("Espera a que termine de cargar la imagen.");
        const blob = await new Promise((resolve) => result.imageData.imageCanvas.toBlob(resolve, "image/png"));
        if (!blob) throw new Error("No se pudo preparar la imagen editada.");
        item.edited = new File([blob], item.file.name.replace(/\.[^.]+$/, "") + ".png", { type: "image/png" });
        if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
        item.previewUrl = URL.createObjectURL(blob);
        item.design = result.designState;
        item.dirty = false;
    }

    async selectItem(id) {
        if (this.state.busy || this.items[this.state.index]?.id === id) return;
        this.state.busy = true;
        this.state.error = "";
        try {
            await this.captureCurrentImage();
            this.state.index = this.items.findIndex((item) => item.id === id);
            this.scheduleEditorMount();
        } catch (error) { this.state.error = error.message; }
        finally { this.state.busy = false; }
    }

    updateDescription(event) { this.current.description = event.target.value; }

    removeItem() {
        if (this.state.busy || !this.current || this.current.uploaded) return;
        this.destroyEditor();
        URL.revokeObjectURL(this.current.url);
        if (this.current.previewUrl) URL.revokeObjectURL(this.current.previewUrl);
        this.items.splice(this.state.index, 1);
        this.state.revision++;
        this.state.index = Math.max(0, Math.min(this.state.index, this.items.length - 1));
        if (!this.items.length) { this.props.close(); return; }
        this.scheduleEditorMount();
    }

    async upload() {
        if (this.state.busy || !this.state.ready || !this.pending.length) return;
        this.state.busy = true;
        this.state.error = "";
        try {
            await this.captureCurrentImage();
            for (const item of this.pending) {
                await this.props.uploadFile(item.edited || item.file, item.description, item.video);
                item.uploaded = true;
                this.state.completed++;
            }
            await this.props.onUploaded();
            this.props.close();
        } catch (error) {
            this.state.error = error?.data?.message || error.message || "No se pudo subir el archivo.";
            await this.props.onUploaded().catch(() => {});
        } finally { this.state.busy = false; }
    }
}
