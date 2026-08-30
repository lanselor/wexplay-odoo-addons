# Wexplay Repair Architecture

## Purpose

`wexplay_repair` is the SAT base module for the current Wexplay repair stack.

It extends `repair.order` with:
- device identification data
- customer reception data
- SAT-oriented search helpers
- a SAT-wide operational label for `state = done` as `Finalizado`
- SAT settings on company/configuration
- DMS helper methods for SAT folders
- invoice/report integrations used by the SAT workflow
- a custom operational card view for repair orders

This module is currently both:
- the functional base for SAT repair operations
- the technical base consumed by `wexplay_repair_workflow` and `wexplay_repair_delivery`

## Current Responsibilities

### `models/repair_order.py`
- Adds SAT fields to `repair.order`
- Keeps Odoo's technical `done` state, but labels it as `Finalizado` for SAT
  because a repair order can close due to successful repair, diagnostic closure,
  customer rejection or non-repairable diagnosis.
- Computes customer summary and SAT totals
- Adds phone/mobile search helper
- Handles basic device-history navigation

### `models/repair_order_dms.py`
- Provides DMS directory helper methods for SAT
- Centralizes SAT folder naming and DMS path resolution

### `models/res_company.py`
- Stores SAT workflow locations per company
- Stores SAT DMS storage and root directory configuration

### `models/res_config_settings.py`
- Exposes SAT company settings in the UI
- Exposes SAT operational deadline settings for the closed `x_sat_priority` catalog

### `models/account_move.py`
- Resolves SAT repairs linked to an invoice
- Exposes SAT invoice print actions
- Routes SAT A4 invoice printing through the shared print stack
- Sends `document_code = sat_a4` for SAT A4 QZ printing

### `models/ir_ui_view.py` and `models/ir_actions_act_window.py`
- Registers the custom `repair_card` view type
- Makes the repair card view the default entry view for repair orders
- Registers and wires the experimental `repair_card_v2` view for iterative SAT UX work

### `static/src/js|xml|scss/repair_order_card_view.*`
- Renders the custom SAT operational card view
- Includes a desktop sidebar with actionable repair alerts for technicians
- Keeps alert rules in Python and limits OWL to presentation and navigation

### `static/src/js|xml|scss/repair_order_card_v2.*`
- Hosts the experimental SAT operational view used to iterate without destabilizing the main card entry
- Reuses the existing repair cards for the central list
- Adds a hero navigation layer based on SAT workflow/stage buckets
- Adds a right-side operational panel that must always follow the active search/filter domain

### `views/repair_order_views.xml`
- Applies the main SAT form customization

### `models/repair_order_sat_report.py`
- Generates the internal SAT technical service report through QWeb.
- Keeps the current generated PDF in the SAT DMS directory.
- Provides download, regeneration, complementary report notes and native email actions.
- Opens Odoo's standard mail composer with the archived PDF as a temporary
  mail attachment and the SAT report template selected.

## Boundaries

This module should remain the base SAT layer.

It should contain:
- stable SAT fields
- shared helpers reused by other repair modules
- company settings needed by the SAT stack
- base UI customizations that are truly common

It should not keep growing with:
- budget-state orchestration
- delivery-specific rules
- payment-triggered behavior
- channel notification rules

Those belong in extender modules.

## SAT Card Views

### `repair_card`

`repair_card` remains the stable SAT card view.

Its purpose is:
- preserve the known operational card design
- remain the safe/default custom SAT card view
- host shared rendering logic reused by `repair_card_v2`

### `repair_card_v2`

`repair_card_v2` is the experimental SAT operational workspace.

It exists to validate UX ideas without forcing unfinished concepts into the
main `repair_card` flow.

Current design intent:
- hero on top for workflow navigation
- central list with the normal SAT repair cards
- right-side operational panel for summaries, alerts and drill-downs

`repair_card_v2` is intentionally allowed to evolve faster than `repair_card`,
but the business rules behind it must still live in Python and remain
reusable.

## Hero Semantics

The top hero in `repair_card_v2` is not driven by SAT priority.

It is driven by SAT workflow/stage meaning and should answer:
`Where in the workflow is the work currently sitting?`

The current buckets are derived from the real SAT flow already modeled through:
- `state`
- `x_budget_stage`
- `product_location_src_id`
- company-configured SAT locations

Current hero buckets:
- `Entrada / Nuevos`
- `En revision`
- `Pendiente cliente`
- `Presupuesto aceptado`
- `Confirmadas`
- `En reparacion`
- `Pendiente repuesto`
- `Pendiente recoger`

Important rule:
- hero buckets must replace each other as navigation
- they must not accumulate as if they were independent long-lived filters

The hero should always feel like stage navigation, not like a strip of CTA buttons.

## SAT Priority Model

`x_sat_priority` has been repurposed as a closed operational SAT catalog.

It now serves two roles at the same time:
- immediate visual importance for technicians
- backend operational policy for deadlines and future alerts

Current closed catalog:
- `normal`
- `urgent`
- `company`
- `warranty`
- `budget`
- `budget_extended`
- `express`

Business rule:
- this catalog is intentionally closed
- users must not be able to create arbitrary extra values from settings
- what is configurable is the timing/policy attached to each existing value,
  not the creation of new categories

## SAT Deadline Policy

For this phase, SAT delay control does not use `schedule_date`.

The deadline source is:
- `create_date`
- plus the configured amount of hours attached to `x_sat_priority`

The priority hour settings live in SAT settings through `res.config.settings`
and `ir.config_parameter`.

Default baseline used in this phase:
- `Normal` -> `72h`
- `Urgente` -> `24h`
- `Empresa` -> `48h`
- `Garantia` -> `72h`
- `Presupuesto` -> `72h`
- `Presupuesto 2` -> `120h`
- `Express` -> `1h`

This deadline policy currently powers:
- overdue detection
- express risk detection
- sidebar alert labeling

## Search, Hero And Sidebar Contract

The current SAT operational views must follow one consistent contract:

- search/filter domain defines the working scope
- hero counts must be recalculated from that active search scope
- sidebar alerts must also be recalculated from that same active search scope

In practice:
- if `Mis ordenes` is active, hero and sidebar must reflect only that technician's queue
- if the filter is removed, hero and sidebar must expand to the wider SAT scope

This contract matters more than visual polish because it keeps all three zones
of the interface honest:
- hero
- central list
- sidebar

## Default Entry Behavior

Current agreed default behavior for the SAT action:
- group by `create_date:day`
- activate `Mis ordenes` by default

Rationale:
- technicians should land first on their own queue
- they must still be able to remove that filter and inspect the wider team load

## Sidebar Scope

The right-side panel is currently still in transition.

Its intended role is not to become a second long list of repair orders.

Its target role is:
- compact operational summaries
- alerts derived from delay/risk conditions
- short drill-down samples only when useful

The current logic already prepares sections such as:
- `Con retraso`
- `Express con riesgo`
- `Pendiente de repuesto`
- `Sin responsable`
- `Confirmadas sin movimiento`

But the visual treatment should continue evolving toward summary-first blocks
instead of heavy stacks of mini-cards.

## Known Architectural Debt

- QZ printing actions reference `wexplay_sat_print` client actions directly.
- The main repair form inheritance is large and therefore more sensitive to upstream view changes.
- There are historical backup files in the module tree that should not be treated as live source.
- The SAT invoice report still resolves repairs directly in QWeb instead of receiving fully prepared values.
- SAT DMS route helpers live in `wexplay_repair`, while part of the DMS company configuration still uses fields introduced by `wex_consent`. This is accepted for now because the repair/consent scope is stable. See `docs/DMS_ROUTE_TECHNICAL_DEBT.md`.
- `repair_card_v2` UX is still intentionally unfinished:
  - hero logic is valid, but visual polish may continue changing
  - sidebar currently mixes useful logic with a presentation that is still too list-heavy
  - scroll interaction between long repair lists and the right panel still needs future refinement

## Printing Notes

- The SAT invoice QWeb report remains correctly located in `wexplay_repair`
- The report itself should not be moved just because QZ execution is shared
- A4 SAT printing now participates in the print stack using `document_code = sat_a4`
- Production validation confirms SAT A4 duplex printing works with:
  - profile `A4 Prod`
  - assignment `SAT A4 Default`
  - duplex mode `Double-sided (long edge)`
- SAT invoice printing should continue to be treated as a functional SAT document owned by `account.move`, not as a detached PDF with no business area

## Technical Service Report

The internal service report is a technical document, not an invoice with extra
information. It must prioritize the incident, initial diagnosis, intervention,
consumed material, technical notes and photographic evidence.

### Document lifecycle

- `x_sat_report_dms_file_id` points to the current report PDF in DMS.
- Generating or regenerating replaces the document with the same deterministic
  SAT filename; it does not create an uncontrolled document history.
- `x_sat_report_notes` stores complementary text that belongs only to the
  report, not to the daily repair notes. If a report already exists, saving
  those notes automatically regenerates the archived PDF.
- The document tab exposes generation, download, regeneration, complementary
  notes and email as compact actions within the report card.

### Layout and content rules

- The report does not show prices, taxes or totals. Commercial amounts belong
  to a quote, proforma or invoice.
- Repair notes may flow over pages when genuinely long. QWeb page-break
  behaviour can move a whole technical block to the next page when it cannot
  fit cleanly; that is preferable to splitting a small structured block.
- Photographic evidence uses one framed image per page so screenshots and
  technical details remain legible without distortion or cropping.
- Images are selected by the existing SAT image-report flag. The report does
  not invent a second manual photo selection workflow.

### Email delivery

- `Enviar` uses `mail.compose.message`, never a custom mail flow.
- The attachment is copied temporarily from the current DMS PDF for the
  composer. It does not create another DMS document or expose a DMS URL.
- The template `SAT - Informe técnico` belongs to `repair.order`, is editable
  through Odoo's template UI and is preselected when opening the composer.
- The sent message and its attachment remain traceable in the SAT chatter.

### Report permissions

Report actions use module-owned groups instead of generic DMS access:

- `Informes Wexplay: Consultar y descargar` can download the report associated with
  a repair the user may read.
- `Informes Wexplay: Generar, editar y enviar` implies the previous group and can
  generate, regenerate, edit complementary notes and send the report.

The groups are created on module installation/update but are not assigned
automatically. DMS access is encapsulated after the repair and report-group
checks, so a user granted report download does not gain general access to SAT
directories or files.

## Notes For Next Phases

- Decide whether QZ printing is a hard dependency or an optional integration.
- Revisit the SAT invoice report so repair resolution is prepared in Python.
- Reduce fragility in the large form inheritance only when there is a concrete business reason to touch it.
- Do not start the print-variant refactor until hybrid behavior is considered stable enough.
- When the configurable-document phase starts, SAT invoice A4 should be modeled as a formal printable document linked to:
  - Odoo model `account.move`
  - SAT functional area
  - its report action
  - its paperformat
