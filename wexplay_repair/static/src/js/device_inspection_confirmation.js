/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export function confirmDeviceInspectionReset(dialog) {
    return new Promise((resolve) => {
        dialog.add(ConfirmationDialog, {
            title: _t("¿Cambiar el tipo de dispositivo?"),
            body: _t("Se borrarán las marcas de ambas caras y los desperfectos seleccionados. La descripción escrita se conservará."),
            confirmLabel: _t("Cambiar y borrar marcas y etiquetas"),
            cancelLabel: _t("Mantener dispositivo"),
            confirm: () => resolve(true),
            cancel: () => resolve(false),
            dismiss: () => resolve(false),
        });
    });
}

export function confirmConsoleInspectionReset(dialog) {
    return new Promise((resolve) => {
        dialog.add(ConfirmationDialog, {
            title: _t("¿Cambiar el formato de consola?"),
            body: _t("Se borrarán las marcas de ambas caras. Las etiquetas y la descripción se conservarán."),
            confirmLabel: _t("Cambiar y borrar marcas"),
            cancelLabel: _t("Mantener formato"),
            confirm: () => resolve(true),
            cancel: () => resolve(false),
            dismiss: () => resolve(false),
        });
    });
}
