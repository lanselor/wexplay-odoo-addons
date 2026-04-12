# Wex Knowledge Technical Rules

## Current rules for this module

- Keep strong permission checks in Python.
- Do not move business-critical access control to OWL or XML.
- Treat dashboard and explorer as UI consumers of article data, not as business-rule owners.
- Keep article workflow decisions centralized in `wex.knowledge.article`.
- Preserve compatibility with Odoo 18 Community.

## Responsive rule

Responsive support is mandatory for this module.

Minimum target devices:
- phone portrait
- phone landscape
- tablet portrait
- tablet landscape
- desktop

Responsive fixes must prioritize:
- layout stability
- readable toolbars
- usable navigation trees
- non-breaking article cards and list rows
- workable article form on tablet and mobile

## Frontend constraints

- Avoid fixed viewport-height layouts when they create nested scrolling issues on mobile.
- Avoid rigid multi-column grids below tablet width.
- Avoid oversized sticky sidebars on narrow screens.
- Prefer stacking and progressive disclosure over horizontal overflow.

## Refactor rule

When refactoring:
- change one layer at a time
- keep the module installable after each phase
- separate Python refactor from responsive CSS work
- do not redesign the information architecture unless there is a functional reason
