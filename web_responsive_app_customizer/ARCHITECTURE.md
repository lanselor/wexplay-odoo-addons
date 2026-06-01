# Web Responsive App Customizer

## Repair Form Footer Base

This module provides a fixed bottom footer for the backend form view of
`repair.order`.

The goal of this footer is to offer a single technical extension point for SAT
actions that must stay visible while the user works inside the repair form,
without moving business logic into `web_responsive_app_customizer`.

### Current status

The footer base is currently present in the module as an experimental
infrastructure, but it should not be considered functionally closed yet.

The shell, assets and extension points exist, but the visual anchoring is still
under revision because the current backend form layout of `repair.order`
combines:

- Odoo form compilation
- `mail` chatter relocation logic
- internal scroll containers from the web client
- responsive behavior from `web_responsive`

This means the remaining problem is not about business logic or extension API,
but about choosing the right DOM anchor and scroll context for a stable bottom
bar.

### Why it lives here

`wexplay_repair` already depends on `web_responsive_app_customizer`, and this
module already contains shared backend UI infrastructure such as the chatter
footer base.

Keeping the repair form footer base here allows:

- one shared frontend injection point
- one shared visual shell
- a clear separation between UI infrastructure and SAT business actions

### Injection strategy

The footer is injected through the backend form compilation layer, by patching
`FormCompiler` and using `FormRenderer` as the runtime context, not by adding a
plain XML block inside the inherited `repair.order` form view.

This is intentional:

- it keeps the footer tied to Odoo's form rendering lifecycle
- it activates by backend model (`repair.order`), not by fragile DOM markers
- it avoids duplicating the footer shell in SAT modules

The footer is rendered inside `.o_form_sheet_bg`, after the main sheet content.

That gives us:

- a stable bottom bar in desktop layouts
- width limited to the repair form block instead of spanning into chatter space
- no overlap with the main form content
- a single place to handle spacing, responsive behavior and visual consistency

### Error observed during implementation

During testing, several intermediate behaviors were observed:

- the footer rendered below the chatter width when anchored too high in the
  form layout
- the footer stayed visually attached to the position where the page was first
  loaded instead of remaining fixed at the bottom while scrolling
- one alternative injection made the footer disappear entirely
- a style compilation error appeared temporarily because of a mobile-safe-area
  CSS expression that was not accepted by the Odoo asset pipeline

The asset compilation error was fixed, but the visual anchoring issue is still
open.

### Paths already tested and discarded

The following approaches were tested and should be treated as explored but not
validated:

- injecting the footer at `web.FormView` level so it becomes a sibling of the
  whole form layout
- trying to keep the footer fixed by syncing its coordinates with JavaScript on
  resize and scroll
- moving the footer after the central form block as a sibling candidate outside
  the sheet area

Those attempts helped clarify the problem, but none of them delivered the final
expected UX.

### Activation rule

The footer base is enabled only when all these conditions are true:

- the current backend form model is `repair.order`
- the form is not rendered inside a dialog

### Base API

The current base methods are patched on `FormRenderer`:

- `_isWexRepairFormFooterEnabled()`
- `_getWexRepairFormFooterClassNames()`
- `_getWexRepairFormFooterBodyClassNames(zone)`

Their responsibility is deliberately small:

- decide whether the shell must exist
- expose footer-level classes
- expose zone-level classes

### Extension strategy for other modules

The footer shell exposes three template anchors:

- `web_responsive_app_customizer.RepairFormFooter.Left`
- `web_responsive_app_customizer.RepairFormFooter.Center`
- `web_responsive_app_customizer.RepairFormFooter.Right`

Modules such as `wexplay_repair`, `wexplay_repair_workflow` or
`wexplay_repair_delivery` should extend those templates to inject their own
buttons, indicators or contextual controls.

This keeps the responsibilities clean:

- `web_responsive_app_customizer` owns the shell
- SAT modules own the actual business actions

### Layout and responsive behavior

The footer is designed as a persistent bottom bar with:

- stable height
- left, center and right zones
- sticky bottom positioning
- print exclusion

Desktop behavior:

- the footer stays anchored at the bottom of the form container
- the main form content keeps its own scroll area

Compact/mobile behavior:

- the zones stack into one column
- the footer keeps its bottom anchoring
- the layout avoids hidden content behind the footer

### Pending technical resolution

The next iteration should start from DOM inspection, not from more blind
positioning changes.

The open technical task is to identify the exact container that:

- belongs only to the main `repair.order` block
- stays outside the chatter width
- participates in the effective scroll behavior seen by the user

Only after that should the final solution be chosen between:

- `sticky` inside the correct scroll container
- a truly fixed bottom bar limited to the main block width
- or a small dedicated wrapper introduced during form compilation

### Guardrails

This base should not:

- contain SAT workflow rules
- decide delivery logic
- hold repair-specific business conditions beyond model activation
- become a second button box with scattered logic

If a new action depends on repair state, permissions or delivery workflow, that
logic should remain in the module that owns the business rule and only render
through one of the footer extension templates.
