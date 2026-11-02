/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.WexPortalBudgetRejection = publicWidget.Widget.extend({
    selector: ".wex_portal_rejection_form",
    events: {
        "change #wexRejectSuggestion": "_onSuggestionChange",
        submit: "_onSubmit",
    },

    _onSuggestionChange(event) {
        const textarea = this.el.querySelector('[name="rejection_reason"]');
        const current = textarea.value.trim();
        if (!current || current === this._lastSuggestion) {
            textarea.value = event.target.value;
        }
        this._lastSuggestion = event.target.value;
    },

    _onSubmit(event) {
        if (this._submitting) {
            event.preventDefault();
            return;
        }
        this._submitting = true;
        this.el.querySelector('button[type="submit"]').disabled = true;
    },
});
