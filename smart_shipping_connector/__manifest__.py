{
    'name': 'Smart Multi-Carrier Shipping & Logistics Connector',
    'version': '17.0.1.0.0',
    'category': 'Shipping',
    'summary': 'Enterprise Multi-Carrier Shipping with Rate Comparison, Label Generation, and Tracking',
    'description': """
        Professional multi-carrier shipping and logistics module for Odoo 17 Enterprise.

        Key Features:
        =============
        * Multi-carrier support (DHL, FedEx, UPS, DPD, Aramex, Custom)
        * Real-time rate shopping and comparison
        * Shipping label generation (PDF)
        * End-to-end shipment tracking
        * Intelligent shipping rules engine
        * Multi-package support
        * Returns management with RMA
        * Batch label generation
        * Customs documentation
        * Insurance and COD support
        * Customer portal access
        * Public tracking pages
        * Advanced dashboard analytics
        * Comprehensive reporting
        * API logging and debugging
        * Multi-company support
        * Security groups: User, Manager, Admin
    """,
    'author': 'Wazirz',
    'website': '',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'stock',
        'stock_delivery',
        'delivery',
        'account',
        'web',
        'portal',
        'board',
        'product',
        'uom',
    ],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',

        # Data
        # 'data/sequences.xml',
        # 'data/carrier_data.xml',
        # 'data/demo_data.xml',
        # 'data/cron_data.xml',
        # 'data/email_templates.xml',
        # 'data/mail_templates.xml',
        # 'data/paper_format.xml',

        # Views - Core
        'views/carrier_views.xml',
        'views/account_views.xml',
        'views/shipment_views.xml',
        'views/shipment_package_views.xml',
        'views/shipment_route_views.xml',
        'views/rate_views.xml',
        'views/rate_request_views.xml',
        'views/rule_views.xml',
        'views/tracking_views.xml',
        'views/return_views.xml',
        'views/dashboard_views.xml',
        'views/shipping_config_views.xml',
        'views/api_log_views.xml',
        'views/customs_views.xml',
        'views/insurance_views.xml',
        'views/notification_views.xml',
        'views/stock_picking_views.xml',

        # Views - Portal & UI
        # 'views/portal_templates.xml',
        'views/menus.xml',
        # 'views/assets.xml',

        # Wizards
        'wizard/rate_shopping_wizard_views.xml',
        'wizard/batch_label_wizard_views.xml',
        'wizard/tracking_update_wizard_views.xml',
        'wizard/import_shipment_wizard_views.xml',
        'wizard/export_manifest_wizard_views.xml',

        # Reports
        'report/shipping_label_report.xml',
        'report/customs_declaration_report.xml',
        'report/packing_slip_report.xml',
        'report/manifest_report.xml',
        'report/return_label_report.xml',
        'report/invoice_report.xml',

        # Actions
        'actions/actions.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'qweb': [
        'static/src/xml/dashboard_templates.xml',
        'static/src/xml/shipment_templates.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 89.00,
    'currency': 'USD',
    'assets': {
        'web.assets_backend': [
            'smart_shipping_connector/static/src/scss/shipping.scss',
            # 'smart_shipping_connector/static/src/js/dashboard.js',
            # 'smart_shipping_connector/static/src/js/shipment.js',
            # 'smart_shipping_connector/static/src/js/tracking.js',
        ],
    },
}
