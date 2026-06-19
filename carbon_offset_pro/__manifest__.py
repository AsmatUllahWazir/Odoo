{
    'name': 'Carbon Offset Pro',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Complete carbon footprint tracking and offset management',
    'description': """
        Carbon Offset Pro - Enterprise Carbon Management

        Features:
        - Carbon Emission Records with source traceability
        - Governance workflow (Draft → Submitted → Verified → Offset)
        - Integration with Maintenance, Sales, and more
        - Carbon offset marketplace with verified projects
        - Generate PDF certificates for customers
        - Sustainability dashboard with charts
        - Email notifications for offset purchases
        - Multi-currency support
        - Configurable scopes, categories, and emission factors
    """,
    'author': 'Wazirz',
    'website': 'https://yourcompany.com',
    'depends': [
        'base',
        'sale',
        'product',
        'mail',
        'web',
        'uom',
    ],
    'data': [
        'security/ir.model.access.csv',
        # 'data/seq_data.xml',
        'data/demo_data.xml',
        # 'data/email_templates.xml',
        # ALL actions must be loaded BEFORE menus that reference them
        'views/product_emission_views.xml',
        'views/carbon_offset_views.xml',
        'views/carbon_scope_category_views.xml',
        'views/carbon_emission_record_views.xml',
        'views/sale_order_views.xml',
        'views/dashboard_views.xml',  # <-- Moved BEFORE menu_views.xml
        # Menus (loaded last, after all actions are defined)
        'views/menu_views.xml',
        'wizard/carbon_offset_wizard_view.xml',
        'reports/report_views.xml',
        'reports/sustainability_report_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'carbon_offset_pro/static/src/css/dashboard.css',
            # 'carbon_offset_pro/static/src/js/dashboard.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
    'price': 35.00,
    'currency': 'USD',
}