# Wex IT Maintenance - Decision Log

## Decision 1. `res.partner` is the customer anchor

The module does not create a parallel customer model.

Reason:
- the maintenance customer is a business contact already represented by `res.partner`
- the flag `x_is_it_maintenance_customer` is enough to scope the app

Implication:
- customer metadata, counters and workspace behavior are implemented as an extension of `res.partner`

## Decision 2. Assets have their own identity

Assets are modeled in [`models/it_asset.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_asset.py) with their own internal code.

Reason:
- an IT asset needs a stable technical identity
- visits and reviews need to reference assets directly

## Decision 3. Visits are the operational center

The main operational unit is `wex.it.maintenance.visit`.

Reason:
- work is performed and reported through visits
- services, work lines, checklist and reviews all converge there

Implication:
- visit state transitions and derived artifacts are currently concentrated in one model

## Decision 4. Reviews are normalized

Asset reviews are not stored as loose notes inside the asset or visit.

Reason:
- review history needs its own normalized model
- this keeps technical history queryable and reusable

Current behavior:
- reviews are generated from visit completion
- one visit can create at most one review per asset

## Decision 5. Checklist templates are copied into visits

Templates are reusable definitions.

Current behavior:
- applying a template clears the current checklist lines
- then recreates checklist lines on the visit from template contents

This is a deliberate copy-on-apply approach, not a live linked template.

## Decision 6. Dashboard is operational, not BI-heavy

The OWL dashboard is meant to be a practical overview, not a complex analytics layer.

Current behavior:
- frontend loads a payload from Python
- dashboard cards and panels act mostly as navigation and summary

Implication:
- business logic should continue to live in Python, not in the dashboard JS

## Decision 7. Credential protection is functional, not yet strong

Current behavior in [`models/it_credential.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_credential.py):
- secrets are hidden in the UI unless the user has the credential group
- there is a dedicated action to reveal the secret in the form context

Important limitation:
- the module does not yet implement strong encryption/key-management for secrets
- this is known technical and security debt

## Decision 8. Be honest about current debt

Known current debt that should remain visible in documentation:
- `it_maintenance_visit.py` is the main concentration point
- `res_partner.py` mixes several responsibilities
- credential storage needs stronger architecture in the future
- the visit report is functional but inline-heavy

## Decision 9. `service` is currently overloaded

The current `wex.it.service` model is useful but semantically too broad.

It can currently be interpreted as:
- a Wexplay responsibility/action
- a managed platform
- a software or licensing item
- a renewal to track
- a network-related element

Target direction:
- keep the current model stable until the concept is redesigned
- separate IT services from software/licensing and networks in a future iteration
- add a customer coverage concept to connect Odoo products, sales and invoices with IT maintenance

## Decision 10. Microsoft 365 is not a credential

Microsoft 365 should be treated as software/licensing or a managed platform.

The credential is the admin access linked to Microsoft 365.

This distinction should guide the future model design:
- platform/software record: what exists and renews
- credential record: how Wexplay accesses it

## Decision 11. Odoo products should be reusable IT templates

Commercial products such as `[GTS] Maintenance up to 3 devices` should remain Odoo products.

Future target:
- an Odoo product can be marked as IT-related
- IT-specific configuration can define standard templates, coverage limits and suggested checks
- selling or invoicing that product can create or update customer IT coverage

This avoids duplicating commercial service definitions per customer.
