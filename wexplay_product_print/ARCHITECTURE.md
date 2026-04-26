# Wexplay Product Print Architecture

## Purpose

`wexplay_product_print` is now restricted to product-specific printing.

It owns:
- product label QWeb report definitions
- product print modal/action
- product-specific controller helpers

It no longer owns the shared QZ core.

## Current Responsibilities

### Product printing flow
1. Open a `product.template` form
2. Click the product print action
3. Open the product print modal
4. Trigger printing through `wex_print_core`

### Product-specific assets
- product modal JS/XML
- product report QWeb
- product-specific signed label controller

## Important Design Notes

- Product printing must enter the shared print router by `document_code`
- The validated production profile for product labels is:
  - `Product Label Prod`
  - printer `Brother QL-710W`
- The validated production assignment is:
  - `Product Label Default`
  - pilot enabled

## Boundaries

This module should contain:
- product-specific reports
- product-specific UI/actions
- product-specific controller endpoints

This module should not contain:
- shared QZ logic
- shared routing
- SAT reports
- shared settings or diagnostics
