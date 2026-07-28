{
    'name': 'Boutique & Small Hotel PMS',
    'version': '17.0.1.0.0',
    'category': 'Hospitality',
    'summary': 'Property Management System for Boutique Hotels and Guesthouses',
    'description': """
        A clean, modern, and easy-to-use Property Management System designed 
        specifically for Boutique Hotels, Guesthouses, and Small Hotels (10-40 rooms).

        Key Features:
        - Complete Room Management with Types, Amenities, and Features
        - Advanced Reservation System with Calendar View
        - Guest Management with History and Preferences
        - Folio and Billing with Service Lines
        - Housekeeping Task Management
        - Service Management
        - Interactive Dashboard with Charts
        - Payment Management
        - Channel Integration
        - Website Booking Form
        - Multiple Reports (Reservation, Folio, Occupancy)
        - Room Status Kanban Board
        - Automated Email Notifications
        - Security Groups (Owner, Manager, Receptionist, Housekeeping)

        Perfect for boutique hotels, guesthouses, and small hotels looking for 
        an elegant and practical management solution.
    """,
    'author': 'Wazirz',
    'website': '',
    'depends': [
        'base',
        'mail',
        'contacts',
        'account',
        'product',
        'sale_management',
        'website',
        'web',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',

        'data/sequences.xml',
        'data/demo_data.xml',
        'data/mail_template_data.xml',

        'views/room_views.xml',
        'views/reservation_views.xml',
        'views/folio_views.xml',
        'views/housekeeping_views.xml',
        'views/service_views.xml',
        'views/guest_views.xml',
        'views/payment_views.xml',
        'views/channel_views.xml',
        'views/hotel_config_views.xml',
        'views/dashboard_views.xml',
        'views/website_templates.xml',
        'views/report_views.xml',
        # 'views/assets.xml',

        'reports/reservation_report.xml',
        'reports/folio_report.xml',
        'reports/occupancy_report.xml',

        'wizards/reservation_wizard_views.xml',
        'wizards/checkout_wizard_views.xml',
        'wizards/payment_wizard_views.xml',
        'wizards/report_wizard_views.xml',
        'wizards/room_change_wizard_views.xml',

        'views/menus.xml',

    ],
    # 'qweb': [
    #     'static/src/xml/dashboard.xml',
    # ],

    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 99.00,
    'currency': 'USD',

    'assets': {
        'web.assets_backend': [
            # 'boutique_hotel_pms/static/src/js/hotel.js',
            # 'boutique_hotel_pms/static/src/js/dashboard.js',
            'boutique_hotel_pms/static/src/scss/hotel.scss',
        ],
        'web.assets_frontend': [
            # 'boutique_hotel_pms/static/src/js/website.js',
            'boutique_hotel_pms/static/src/scss/website.scss',
        ],
    },
}