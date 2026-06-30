{
    'name': 'Salon & Spa Management',
    'version': '18.0.1.0.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Complete POS, appointment, and membership management for salons and spas.',
    'description': """
        Comprehensive management system for salons and spas:
        - Online and POS appointment booking
        - Staff/beautician scheduling and commission
        - Chair/resource allocation
        - Membership management
        - POS integration
        - Customer history and loyalty
        - Inventory management for salon products
        - Revenue analytics and reporting
    """,
    'author': 'Wazirz',
    'website': '',
    'depends': ['base', 'sale', 'account', 'point_of_sale', 'hr', 'mail', 'web', 'contacts', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'security/salon_security.xml',
        'data/salon_data.xml',
        'views/salon_service_views.xml',
        'views/salon_appointment_views.xml',
        'views/salon_order_views.xml',
        'views/salon_chair_views.xml',
        'views/salon_membership_views.xml',
        'views/salon_commission_views.xml',
        'views/salon_dashboard_views.xml',
        'views/salon_templates.xml',
        # 'views/pos_salon_templates.xml',
        'views/res_partner_views.xml',
        'views/salon_product_kit_views.xml',
        'report/salon_report_templates.xml',
        'report/salon_report_views.xml',
        'report/salon_report_wizard_views.xml',
        'views/salon_menus.xml',
    ],
    'qweb': ['static/src/xml/pos_salon.xml'],
    'demo': ['data/salon_demo.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 79.00,
    'currency': 'USD',
    'images': ['static/description/icon.png'],
}