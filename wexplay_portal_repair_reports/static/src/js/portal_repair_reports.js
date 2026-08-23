/** @odoo-module **/

function getFilename(contentDisposition) {
    const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match) {
        return decodeURIComponent(utf8Match[1]);
    }
    const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
    return filenameMatch ? filenameMatch[1] : "informe-tecnico.pdf";
}

function setLoadingState(container, isLoading) {
    const buttons = container.querySelectorAll("[data-wex-portal-report-download]");
    buttons.forEach((button) => {
        const icon = button.querySelector("[data-wex-portal-report-icon]");
        const label = button.querySelector("[data-wex-portal-report-label]");
        if (isLoading) {
            button.dataset.originalLabel = label.textContent;
            button.setAttribute("aria-disabled", "true");
            button.classList.add("is-loading");
            icon.className = "fa fa-spinner fa-spin me-1";
            label.textContent = "Generando informe...";
            return;
        }
        button.removeAttribute("aria-disabled");
        button.classList.remove("is-loading");
        icon.className = "fa fa-download me-1";
        label.textContent = button.dataset.originalLabel;
    });
}

function showFeedback(container, message, isError = false) {
    const feedback = container.querySelector("[data-wex-portal-report-feedback]");
    feedback.textContent = message;
    feedback.classList.toggle("is-error", isError);
    feedback.hidden = false;
}

function initializeLogoPreview() {
    const input = document.querySelector("[data-wex-portal-logo-input]");
    if (!input) {
        return;
    }
    const preview = input.closest(".col-12")?.querySelector("[data-wex-portal-logo-preview]");
    const image = preview?.querySelector("[data-wex-portal-logo-image]");
    const placeholder = preview?.querySelector("[data-wex-portal-logo-placeholder]");
    const status = preview?.querySelector("[data-wex-portal-logo-status]");
    if (!preview || !image || !placeholder || !status) {
        return;
    }

    input.addEventListener("change", () => {
        const [file] = input.files;
        if (!file) {
            return;
        }
        if (!file.type.startsWith("image/")) {
            status.textContent = "Selecciona una imagen válida para el logotipo.";
            return;
        }
        const reader = new FileReader();
        reader.addEventListener("load", () => {
            image.src = reader.result;
            image.hidden = false;
            placeholder.hidden = true;
            status.textContent = `Nuevo logotipo seleccionado: ${file.name}. Guarda la identidad para aplicarlo.`;
        });
        reader.readAsDataURL(file);
    });
}

document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-wex-portal-report-download]");
    if (!button) {
        return;
    }
    if (button.getAttribute("aria-disabled") === "true") {
        event.preventDefault();
        return;
    }
    const container = button.closest("[data-wex-portal-report-actions]");
    if (!container) {
        return;
    }

    event.preventDefault();
    setLoadingState(container, true);
    showFeedback(container, "Generando el informe. La descarga comenzará automáticamente.");
    try {
        const response = await fetch(button.href, { credentials: "same-origin" });
        if (!response.ok || !response.headers.get("Content-Type")?.includes("application/pdf")) {
            throw new Error("report_generation_failed");
        }
        const pdf = await response.blob();
        const link = document.createElement("a");
        const objectUrl = URL.createObjectURL(pdf);
        link.href = objectUrl;
        link.download = getFilename(response.headers.get("Content-Disposition") || "");
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        showFeedback(container, "Informe generado. La descarga ha comenzado.");
    } catch {
        showFeedback(container, "No se ha podido generar el informe. Inténtalo de nuevo.", true);
    } finally {
        setLoadingState(container, false);
    }
});

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeLogoPreview, { once: true });
} else {
    initializeLogoPreview();
}
