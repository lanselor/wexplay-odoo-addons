# Wexplay SAT Print Architecture

## Purpose

`wexplay_sat_print` contains SAT-specific printing flows.

It owns:
- SAT labels
- SAT ticket
- SAT print center/modal
- SAT client actions

It reuses `wex_print_core` for the shared technical printing layer.

## Current Responsibilities

### SAT modal and actions
- SAT print center modal
- SAT direct client actions for label/ticket printing
- generic SAT-side action to print a QWeb report through QZ

### SAT QWeb reports
- repair label `29x90`
- repair label `29x42`
- thermal ticket `80x170`

## Important Design Notes

- SAT actions should enter the shared router through `document_code` whenever possible
- SAT A4 from invoices is triggered from `wexplay_repair`, but the technical QZ execution still goes through this stack
- SAT print actions must keep the ability to fall back to `legacy`

## Boundaries

This module should contain:
- SAT-specific report definitions
- SAT-specific client actions
- SAT-specific modal UX

This module should not contain:
- shared QZ settings
- shared routing logic
- shared diagnostics
- product printing logic
