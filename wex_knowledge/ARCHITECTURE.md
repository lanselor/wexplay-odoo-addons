# Wex Knowledge Architecture

## Purpose

`wex_knowledge` provides an internal knowledge base for Odoo 18 Community with:
- editorial articles
- categories and tags
- a custom dashboard
- a custom explorer
- cross-links to business records such as repairs, sales, purchases, stock pickings and products

The module is meant to be an operational internal tool, not a decorative portal.

## Main building blocks

- `wex.knowledge.article`
  Core domain model. Stores article content, workflow state, visibility, ownership, hierarchy and related records.
- `wex.knowledge.category`
  Hierarchical taxonomy for article grouping. Can be global or company-specific.
- `wex.knowledge.tag`
  Company-scoped tag model used for lightweight classification.
- `wex.knowledge.article.link`
  Generic relation model used to link articles to concrete business records.

## UI structure

- Client action dashboard
  Entry point focused on discovery, recent content and shortcuts.
- Client action explorer
  Search, filtering, tree navigation and card/list rendering.
- Article form
  Editorial workspace with metadata sidebar, HTML editor and related records.

## Security model

Three functional roles exist:
- `Knowledge User`
- `Knowledge Editor`
- `Knowledge Manager`

Security is enforced in two layers:
- record rules for read/write scope
- Python checks in `create()`, `write()`, `unlink()` and lock-related actions

Important rule:
- critical permission logic lives in Python, not only in the UI

## Related-model integration

The module extends:
- `repair.order`
- `purchase.order`
- `sale.order`
- `stock.picking`
- `product.template`

Each extension adds:
- a stat button
- a computed article count
- an action that opens the filtered article library for the model

## Current architectural risks

- `knowledge_article.py` concentrates too much responsibility
- dashboard/explorer payload preparation is tightly coupled to the main article model
- the custom SCSS is large and desktop-first
- responsive behavior is currently insufficient on phone and uneven on tablet

## Refactor direction

The target direction is incremental:
- keep business rules centralized in Python
- keep client actions for navigation and UX
- reduce payload and tree-building complexity in the main model over time
- make the frontend responsive without redesigning the whole module
