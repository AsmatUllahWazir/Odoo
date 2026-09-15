# Saudi HR Government Compliance Hub + Muqeem Workforce Operations

Odoo 17 operations platform combining Saudi HR compliance, residency/Iqama lifecycle management, government-service workflows, travel readiness, document gates, approvals, payment gates, SLA monitoring, transaction audit, GOSI/WPS readiness, EOS and clearance workflows, dashboards, portal pages and PDF reports.

## Odoo 17 XML conventions

- List views use `<tree>` (Odoo 17 view architecture).
- Each XML view file declares view records first and window actions last.
- Menu items live only in `views/menu_views.xml`.
- The manifest loads `menu_views.xml` after all action definitions.
- Python uses regular indentation and explicit multi-line control-flow blocks.
- View IDs and view names use `.tree` for tree views.

## Integration boundary

The module provides a provider-neutral transaction layer. It does not impersonate or fabricate Muqeem/Qiwa/GOSI/Mudad government APIs. Approved provider adapters can be connected to the transaction queue.

## Validation

The release package is statically validated for Python syntax, XML well-formedness, Odoo 17 tree-view usage, action ordering, menu isolation, manifest references, and internal XML action/view references. Runtime installation against a real Odoo 17 server/database is still required for final deployment certification.
