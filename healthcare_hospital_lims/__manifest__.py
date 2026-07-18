{
    'name': 'Hospital Laboratory Information Management System',
    'version': '17.0.1.0.0',
    'category': 'Healthcare',
    'summary': 'Comprehensive Laboratory Information Management System',
    'description': """
        Hospital LIMS - Laboratory Information Management System
        ========================================================
        Complete solution for managing laboratory operations in healthcare settings.

        Features:
        - Patient Management with Medical History
        - Test Order Processing with Workflow
        - Sample Tracking with Barcode Support
        - Result Entry with Auto-validation
        - Quality Control Management
        - Professional PDF Reports
        - Automatic Invoicing
        - Dashboard Analytics
        - Email Notifications
        - Activity Tracking
        - Patient Portal
        - API Integration
    """,
    'author': 'Wazirz',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'mail',
        'product',
        'sale',
        'account',
        'contacts',
        'hr',
        'web',
        'website',
    ],
    'data': [
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/demo_data.xml',
        'data/mail_templates.xml',
        'views/lims_patient_views.xml',
        'views/lims_test_type_views.xml',
        'views/lims_sample_views.xml',
        'views/lims_test_order_views.xml',
        'views/lims_test_order_line_views.xml',
        'views/lims_result_template_views.xml',
        'views/lims_quality_control_views.xml',
        'views/lims_instrument_views.xml',
        'views/lims_report_views.xml',
        'views/dashboard_views.xml',
        'views/lims_wizard_views.xml',
        'views/portal_templates.xml',
        'reports/lims_report_templates.xml',
        'views/menus.xml',
    ],

    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 99.00,
    'currency': 'USD',
}