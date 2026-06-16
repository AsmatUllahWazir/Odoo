{
    'name': 'Carbon Offset Pro',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Complete carbon footprint tracking and offset management',
    'description': """
        Carbon Offset Pro - Enterprise Carbon Management

        Features:
        - Track carbon footprint per product and order
        - Carbon offset marketplace with verified projects  
        - Generate PDF certificates for customers
        - Sustainability dashboard with charts
        - Email notifications for offset purchases
        - Multi-currency support
        - Real-time carbon footprint calculator
        - PDF reports with emission breakdowns
        - Auto-offset configuration
        - API endpoints for external integration
    """,
    'author': 'Wazirz',
    'website': 'https://yourcompany.com',
    'depends': [
        'base',
        'sale',
        'product',
        'mail',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        # 'security/security_groups.xml',
        # 'data/seq_data.xml',
        # 'data/email_templates.xml',
        # 'data/demo_data.xml',
        'views/product_emission_views.xml',
        'views/sale_order_views.xml',
        'views/carbon_offset_views.xml',
        'views/dashboard_views.xml',
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
    'price': 15.00,
    'currency': 'USD',
}