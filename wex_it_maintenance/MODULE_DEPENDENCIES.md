# Wex IT Maintenance - Module Dependencies

## Declared dependencies

Current manifest: [`__manifest__.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/__manifest__.py)

### `mail`

Required.

Used by:
- `mail.thread`
- `mail.activity.mixin`

Present in:
- [`models/it_asset.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_asset.py)
- [`models/it_service.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_service.py)
- [`models/it_maintenance_visit.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_maintenance_visit.py)
- [`models/it_credential.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_credential.py)

### `web`

Required.

Used by:
- OWL dashboard client action
- backend assets bundle

Present in:
- [`static/src/js/it_maintenance_dashboard.js`](/C:/odoo18/addons-wexplay/wex_it_maintenance/static/src/js/it_maintenance_dashboard.js)
- [`static/src/xml/it_maintenance_dashboard.xml`](/C:/odoo18/addons-wexplay/wex_it_maintenance/static/src/xml/it_maintenance_dashboard.xml)
- [`static/src/scss/it_maintenance.scss`](/C:/odoo18/addons-wexplay/wex_it_maintenance/static/src/scss/it_maintenance.scss)

## Redundant dependency

### `base`

Redundant.

Odoo modules implicitly depend on `base`, so it should not be declared unless there is a very specific reason.

## Implicit/native coupling worth documenting

### `res.partner`

The module extends `res.partner` heavily in:
- [`models/res_partner.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/res_partner.py)
- [`views/res_partner_views.xml`](/C:/odoo18/addons-wexplay/wex_it_maintenance/views/res_partner_views.xml)

This is native extension, not a separate module dependency concern, but it is a real architectural coupling.

### QWeb reporting stack

The visit report depends on the native QWeb/report stack:
- [`reports/it_maintenance_visit_report.xml`](/C:/odoo18/addons-wexplay/wex_it_maintenance/reports/it_maintenance_visit_report.xml)

No extra custom reporting dependency is introduced.

## Dependencies intentionally not present

- no `web_editor`
- no `project`
- no `stock`
- no `repair`
- no DMS dependency in current implementation

This is good and keeps the module relatively self-contained.

## Future dependency decisions to watch

### Strong credential security

If credential storage is hardened in a future iteration, dependency decisions may change depending on the chosen storage/encryption strategy.

### Document management

If visit reports, attachments or customer IT documentation later move into a more formal document strategy, a DMS dependency may become relevant, but it is not part of the current implementation.
