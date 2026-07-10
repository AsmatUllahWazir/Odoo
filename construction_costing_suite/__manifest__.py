{
    'name': 'Construction & Project Costing Management Suite',
    'version': '1.0.0',
    'category': 'Construction',
    'summary': 'Complete construction project management with job costing, BOQ, progress billing',
    'description': """
        Comprehensive Construction Management Solution
        ==============================================

        Transform your construction project management with our all-in-one suite that integrates 
        project planning, cost control, and financial management seamlessly with Odoo.

        Key Features:
        -------------
        • Bill of Quantities (BOQ) Management with Excel import
        • Real-time Job Costing & Budget Control Dashboard
        • Automated Material Requisitions & Site Inventory
        • Progress Billing with Milestone & % Completion
        • Subcontractor Management Portal
        • Safety & Compliance Checklists
        • Advanced Project Scheduling with Gantt views
        • Client Portal for project tracking
        • Comprehensive Reporting Suite
    """,
    'author': 'Wazirz',
    'website': '',
    'depends': [
        'base',
        'project',
        'account',
        'sale_management',
        'purchase',
        'stock',
        'hr_timesheet',
        'portal',
        'mail',
        'web',
        'web_gantt',
    ],
    'data': [
        'security/construction_security.xml',
        'security/ir.model.access.csv',
        'views/construction_views.xml',
        'views/construction_task_views.xml',
        'views/boq_views.xml',
        'views/checklist_views.xml',
        'views/material_requisition_views.xml',
        'views/job_cost_views.xml',
        'views/progress_billing_views.xml',
        'views/subcontractor_views.xml',
        'views/dashboard_views.xml',
        'views/report_views.xml',
        'views/menu_views.xml',
        'wizards/import_boq_wizard.xml',
        'wizards/generate_invoice_wizard.xml',
        'wizards/close_project_wizard.xml',
        'views/portal_templates.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'demo/construction_data.xml',
        'demo/demo_users.xml',
        'demo/demo_projects.xml',
        'demo/demo_boq.xml',
        'demo/demo_transactions.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'construction_costing_suite/static/src/css/dashboard.css',
            # 'construction_costing_suite/static/src/js/dashboard.js',
        ],
        'web.assets_frontend': [
            'construction_costing_suite/static/src/css/portal.css',
        ],
    },

    'images': ['static/description/icon.png'],

    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 65.00,
    'currency': 'USD',
}