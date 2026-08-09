{
    'name': 'Smart Direct Print',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Direct printing system for Odoo 19',
    'description': """
        Smart Direct Print Module
        =========================

        This module provides direct printing functionality for Odoo 19,
        allowing users to send PDF, ZPL, and other printable documents
        directly to configured network printers without downloading.

        Key Features:
        -------------
        * Direct printing to network/local printers
        * Print server integration via REST API
        * Intelligent printer selection rules
        * Automatic print scenarios for workflows
        * Manual print operations wizard
        * Support for multiple document formats (PDF, ZPL, ESC/POS, RAW)
        * Print job monitoring and management
        * Multi-company support
        * User-specific printer preferences

        The module works with a lightweight print bridge service
        that connects Odoo to physical printers.
    """,
    'author': 'Wazirz',
    'website': '',
    'depends': [
        'base',
        'mail',
        'web',
        'sale',
        'purchase',
        'account',
        'stock',
        'delivery',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        # 'data/print_scenario_data.xml',
        'data/print_scenario_action_data.xml',
        'views/printer_views.xml',
        'views/print_server_views.xml',
        'views/print_job_views.xml',
        'views/print_rule_views.xml',
        'views/print_scenario_views.xml',
        'views/print_scenario_action_views.xml',
        'views/print_report_views.xml',
        'views/print_attachment_views.xml',
        # 'views/res_users_views.xml',
        'wizard/print_operations_views.xml',
        # 'views/assets.xml',
        'views/menu_views.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'smart_direct_print/static/src/css/direct_print.css',
    #         'smart_direct_print/static/src/js/print_service.js',
    #         'smart_direct_print/static/src/js/print_button.js',
    #         'smart_direct_print/static/src/js/print_dialog.js',
    #         'smart_direct_print/static/src/js/print_status.js',
    #     ],
    # },

    'images': ['static/description/icon.png'],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 0.00,
    'currency': 'USD',

}