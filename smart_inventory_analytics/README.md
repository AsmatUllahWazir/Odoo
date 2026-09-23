# Smart Inventory Aging, Dead Stock & Reorder Analytics

**Version 17.0.2.0.0** — Enhanced starter for Odoo 17

## Features

### Core Analytics (extends product.product)
- Last move date & days since last movement
- Aging buckets: 0-30 / 31-60 / 61-90 / 90+ / No movement
- Dead stock flag + composite score
- 30-day sold qty & turnover rate
- Suggested reorder quantity + priority (none/low/medium/high/critical) + reason

### Aging Analyses
- Snapshot model with full lines
- Bucket distribution totals
- Dead stock value & high-priority reorder count
- Run on demand or via scheduled action (cron)

### Dashboard (OWL)
- KPI cards: products with stock, dead stock count/value, total value, high-priority reorders
- Aging bucket distribution
- Top dead stock by score
- Top reorder priorities

### Reports
- Flexible PDF wizard (bucket, dead-only, high-priority, product filter, company)
- Professional layout with summary cards + detailed table

### Portal
- `/my/inventory/aging` — filterable & sortable list for users with access
- Entry on portal home

### Configuration
- Dead stock threshold (days) in Inventory settings
- Optional daily automatic analysis (activate the cron)

## Installation

1. Place `smart_inventory_analytics` in your addons path
2. Update Apps list
3. Install the module
4. Assign **Smart Inventory Analytics / User** or **Manager** group
5. (Optional) Set dead-stock days under Inventory → Configuration → Settings
6. (Optional) Activate the scheduled action “Smart Inventory: Daily Aging Analysis”

## Menu

**Inventory → Inventory Analytics**
- Dashboard
- Product Aging
- Aging Analyses
- Print Aging Report

## Technical Notes

- Clean inheritance of core models
- Stored computed fields for performance on lists
- Multi-company aware
- LGPL-3

This is a strong, production-oriented foundation. Extend with Excel export, more charts, automatic purchase suggestions, or warehouse-specific rules as needed.
