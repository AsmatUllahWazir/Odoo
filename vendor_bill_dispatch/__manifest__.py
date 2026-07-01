# -*- coding: utf-8 -*-
{
    'name': 'Vendor Bill Dispatch - Multi-Company OCR Automation',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Centralized OCR processing and automatic vendor bill dispatch across multiple companies',
    'description': """
        Vendor Bill Dispatch System
        ============================

        This module provides a complete solution for centralizing vendor bill processing
        across multiple companies with automatic OCR, intelligent dispatch, and multi-level
        validation workflows.

        Key Features:
        ------------
        * Centralized bill reception via email or manual upload
        * Automatic OCR processing with Odoo Document Digitization
        * Smart dispatch rules based on vendor, IBAN, currency, keywords, etc.
        * Multi-level approval workflow (Business → Finance → Accounting)
        * Complete audit trail and traceability
        * Multi-company security and separation
        * KPI dashboard for monitoring performance

        Similar to: Zendoc, Basware, Coupa invoice automation
    """,
    'author': 'ABCG Gul-e-Daman Society',
    'website': 'https://www.abcg.io',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'account_accountant',
        'documents',
        'documents_account',
        'iap',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',
        'security/multi_company_rules.xml',

        # Data
        'data/mail_templates.xml',
        'data/ir_cron.xml',
        'data/sequence.xml',
        'data/dispatch_config_data.xml',


        # Views
        'views/dispatch_rule_views.xml',
        'views/vendor_bill_dispatch_config_views.xml',
        'views/account_move_views.xml',
        'views/validation_history_views.xml',
        'views/dashboard_views.xml',
        'views/menu_views.xml',

        # Wizards
        'wizard/reject_invoice_wizard_views.xml',
        'wizard/manual_dispatch_wizard_views.xml',
        'wizard/bulk_approve_wizard_views.xml',

        # Reports
        # 'report/dispatch_report_templates.xml',
        # 'report/kpi_report_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vendor_bill_dispatch/static/src/css/dashboard.css',
            'vendor_bill_dispatch/static/src/js/dashboard_widget.js',
            'vendor_bill_dispatch/static/src/xml/dashboard_templates.xml',
        ],
    },
    'demo': [
        'demo/demo_data.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 59.00,
    'currency': 'USD',
    'post_init_hook': 'post_init_hook',
}