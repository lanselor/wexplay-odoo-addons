# Wex IT Maintenance - Architecture

## Purpose

`wex_it_maintenance` models the IT maintenance service that Wexplay provides to business customers.

The module is built around:
- IT maintenance customers on `res.partner`
- assets with their own identity
- maintenance visits as the main operational unit
- asset reviews as normalized technical history
- services currently managed for each customer
- credentials linked to customer, asset or service
- a lightweight operational dashboard
- a QWeb report for completed visits

The target conceptual vocabulary is documented in [`CONCEPTUAL_MODEL.md`](/C:/odoo18/addons-wexplay/wex_it_maintenance/CONCEPTUAL_MODEL.md).

## Main business objects

### `res.partner`

Extended in [`models/res_partner.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/res_partner.py).

Responsibilities:
- mark whether a partner is an IT maintenance customer
- store service-level and contract metadata
- act as customer workspace entry point
- expose smart buttons, counters and workspace metrics

This is the customer anchor of the application.

### `wex.it.asset`

Defined in [`models/it_asset.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_asset.py).

Responsibilities:
- give each managed asset its own identity
- link the asset to one maintenance customer
- store technical and operational information
- generate an internal code per customer and asset type

### `wex.it.service`

Defined in [`models/it_service.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_service.py).

Responsibilities:
- currently represent customer-managed services separately from assets
- track service type, status and renewal date
- relate services to visits and credentials

Important limitation:
- the current concept is too broad
- it can represent actions Wexplay performs, managed platforms, renewals or software-like elements
- the target model should separate IT services, software/licensing, networks and customer coverage

### `wex.it.maintenance.visit`

Defined in [`models/it_maintenance_visit.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_maintenance_visit.py).

This is the main operational model.

Responsibilities:
- schedule and execute preventive or corrective work
- record work lines and checklist lines
- relate services touched during the visit
- generate asset reviews on completion
- provide dashboard payload data

### `wex.it.asset.review`

Defined in [`models/it_asset_review.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_asset_review.py).

Responsibilities:
- persist normalized technical review history
- keep one review linked to an asset and, optionally, to a visit

### `wex.it.credential`

Defined in [`models/it_credential.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_credential.py).

Responsibilities:
- store credentials linked to customer, asset or service
- restrict UI access to secret values by group
- synchronize customer/company from linked asset or service

Important note:
- current protection is functional and UI-based
- secrets are not yet implemented with strong encryption/key-management architecture

### `wex.it.maintenance.template`

Defined in [`models/it_maintenance_template.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_maintenance_template.py).

Responsibilities:
- store reusable checklist templates for visits

## Frontend layer

Dashboard files:
- [`static/src/js/it_maintenance_dashboard.js`](/C:/odoo18/addons-wexplay/wex_it_maintenance/static/src/js/it_maintenance_dashboard.js)
- [`static/src/xml/it_maintenance_dashboard.xml`](/C:/odoo18/addons-wexplay/wex_it_maintenance/static/src/xml/it_maintenance_dashboard.xml)
- [`static/src/scss/it_maintenance.scss`](/C:/odoo18/addons-wexplay/wex_it_maintenance/static/src/scss/it_maintenance.scss)

Current role of the frontend:
- load dashboard data from Python
- render cards and quick navigation
- keep interaction thin

Business logic is still correctly concentrated in Python.

## Reporting

Visit report:
- [`reports/it_maintenance_visit_report.xml`](/C:/odoo18/addons-wexplay/wex_it_maintenance/reports/it_maintenance_visit_report.xml)

Current role:
- render the completed visit as a service report
- display customer, technician, work lines, checklist and recommendations

Current limitation:
- layout is heavily inline-styled and presentation-focused
- report preparation is still basic and can be improved later

## Current architectural strengths

- domain is clearly split into models
- visit is correctly the operational center
- reviews are normalized into their own model
- dashboard is thin and reads from Python
- multi-company rules are present
- tests already exist

## Current architectural pressure points

- [`models/it_maintenance_visit.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/it_maintenance_visit.py) concentrates too much responsibility
- [`models/res_partner.py`](/C:/odoo18/addons-wexplay/wex_it_maintenance/models/res_partner.py) mixes extension, metrics and navigation
- `wex.it.service` is conceptually overloaded
- there is no dedicated customer coverage layer linking Odoo products/invoices with IT maintenance
- credentials are functionally restricted but not strongly secured yet
- report layout is rigid and inline-heavy

## Recommended refactor order

1. documentation and manifest cleanup
2. refactor `it_maintenance_visit.py`
3. refactor `res_partner.py`
4. review credential security architecture
5. refine dashboard/report only after backend is cleaner
