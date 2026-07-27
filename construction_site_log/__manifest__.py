{
    'name': 'Construction Site Daily Log & Safety Compliance',
    'version': '17.0.1.0.0',
    'category': 'Construction',
    'summary': 'Comprehensive site daily logging and safety compliance system',
    'description': """
        Professional Construction Site Daily Log and Safety Compliance System.
        Features:
        - Daily site logs with weather, manpower, materials, and progress tracking
        - Safety observations and incident reporting
        - Toolbox talks management
        - Safety checklists
        - Automatic PDF report generation
        - Integration with Project, Timesheet, and Inventory modules
        - Dashboard with real-time statistics
        - Portal access for external users
    """,
    'author': 'Wazirz',
    'website': '',
    'depends': [
        'base',
        'mail',
        'project',
        'hr',
        'hr_timesheet',
        'stock',
        'account',
        'portal',
        'web'
    ],
    'data': [
        # 'security/module_category.xml',
        'security/security_groups.xml',
        'security/ir.model.access.csv',

        'data/sequences.xml',
        'data/demo_data.xml',
        'data/email_templates.xml',

        'views/daily_log_views.xml',
        'views/safety_views.xml',
        'views/incident_views.xml',
        'views/toolbox_views.xml',
        'views/checklist_views.xml',
        'views/dashboard_views.xml',
        'views/portal_templates.xml',

        'wizards/daily_log_wizard_views.xml',

        'reports/daily_log_report.xml',
        'reports/daily_log_report_templates.xml',

        'views/menus.xml',
    ],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            # 'construction_site_log/static/src/js/dashboard.js',
            # 'construction_site_log/static/src/scss/dashboard.scss',
        ],
        'web.assets_frontend': [
            # 'construction_site_log/static/src/scss/portal.scss',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 59.00,
    'currency': 'USD',
}
