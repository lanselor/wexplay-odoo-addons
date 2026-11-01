# Browser integration check
Requires Node, Playwright available through NODE_PATH (or local installation outside the addon), and Chrome.
Run node wexplay_repair_images/tests/browser/upload_dialog.cjs from the repository.
Optional OWL_PATH and CHROME_PATH point to the local Odoo owl.js bundle and browser executable.
Uses actual OWL and vendored editor, a minimal Dialog stand-in and mocked upload callback; no database or live SAT changes.
Checks gallery description preservation, drawing/export and partial-failure retry without duplicate acknowledged uploads.
Odoo Dialog/service styling and actual ORM/DMS remain end-to-end manual checks.

Compile the actual SCSS with Odoo bundled Python: python wexplay_repair_images/tests/browser/check_styles.py (requires libsass). This catches Sass evaluation of CSS math with incompatible units.

Regression for real dialog-service lifecycle: node wexplay_repair_images/tests/browser/odoo_dialog_lifecycle.cjs. ODOO_WEB_PATH optionally points to addons/web/static. Loads real overlay/dialog services and templates; auxiliary UI hooks and network callbacks are mocked. Covers opening, closing, reopening, submission and busy-close guard, with host-side watchdog. This regression was absent from the first isolated component test.
