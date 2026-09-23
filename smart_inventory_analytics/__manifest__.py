{
    'name': 'Smart Inventory Aging, Dead Stock & Reorder Analytics',
    'version': '17.0.2.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Advanced inventory aging, dead stock detection, turnover analytics, reorder engine, beautiful dashboards and professional reports',
    'description': """
Smart Inventory Aging, Dead Stock & Reorder Analytics
=====================================================

A comprehensive analytics layer on top of Odoo Inventory:

* Product-level aging buckets (0-30 / 31-60 / 61-90 / 90+ / No movement)
* Dead stock scoring and automatic flagging
* Turnover rate & velocity analysis
* Intelligent reorder suggestions with priority
* Snapshot-based Aging Analyses
* Modern OWL dashboard with KPIs, aging distribution and top offenders
* Professional PDF reports + wizard filters
* Manager portal views
* Configurable thresholds and scheduled analysis
* Security groups and multi-company ready

Designed for real inventory managers who need visibility beyond standard stock reports.
    """,
    'author': 'Your Company',
    'website': 'https://www.example.com',
    'license': 'LGPL-3',
    'depends': [
        'stock',
        'product',
        'mail',
        'portal',
        'web',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_config_parameter_data.xml',
        'views/res_config_settings_views.xml',
        'views/product_views.xml',
        'views/inventory_aging_views.xml',
        'views/dashboard_views.xml',
        'views/menus.xml',
        'views/portal_templates.xml',
        'report/inventory_aging_report.xml',
        'report/inventory_aging_report_templates.xml',
        'wizard/aging_report_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'smart_inventory_analytics/static/src/css/dashboard.css',
            'smart_inventory_analytics/static/src/js/dashboard.js',
            'smart_inventory_analytics/static/src/xml/dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
