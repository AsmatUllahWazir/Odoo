{
    'name': 'Saudi Muqeem Workforce Operations',
    'version': '17.0.2.0.0',
    'category': 'Human Resources/Saudi Arabia',
    'summary': 'Saudi Muqeem workforce operations, documents, government workflows, EOS, GOSI, WPS readiness and employee portal',
    'description': '''
Saudi Muqeem Workforce Operations
==================================
A compliance operations layer for Odoo HR. It centralizes employee government
identifiers, Iqama/passport/work-permit documents, expiry monitoring, compliance
cases, EOS requests, GOSI profiles, WPS readiness, government transactions,
clearance/offboarding, dashboards, portal access and printable reports.

The module intentionally does not claim to provide direct government API access.
Integration adapters can be connected to approved Muqeem/Qiwa/GOSI/Mudad providers.
''',
    'author': 'Wazirz',
    'website': '',
    'depends': ['hr', 'mail', 'portal', 'hr_contract', 'web'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/muqeem_rules.xml',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/compliance_rules.xml',
        'data/mail_template_data.xml',
        'data/muqeem_data.xml',
        'data/muqeem_cron.xml',
        'views/muqeem_views.xml',
        'views/muqeem_dashboard_views.xml',
        'views/muqeem_portal_templates.xml',
        'reports/muqeem_reports.xml',
                'views/res_config_settings_views.xml',
        'views/government_service_views.xml',
        'views/dependent_views.xml',
        'views/compliance_action_views.xml',
        'views/audit_views.xml',
        'views/wizard_views.xml',
        'views/hr_employee_views.xml',
        'views/compliance_document_views.xml',
        'views/government_transaction_views.xml',
        'views/compliance_case_views.xml',
        'views/eos_views.xml',
        'views/gosi_views.xml',
        'views/wps_views.xml',
        'views/clearance_views.xml',
        'views/dashboard_views.xml',
        'views/portal_templates.xml',
        'reports/report_templates.xml',
        'reports/report_actions.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'saudi_muqeem_workforce_operations/static/src/css/compliance_backend.css',
            'saudi_muqeem_workforce_operations/static/src/css/muqeem_command_center.css',
            'saudi_muqeem_workforce_operations/static/src/css/muqeem_portal.css',
            # 'saudi_muqeem_workforce_operations/static/src/js/compliance_dashboard.js',
        ],
        'web.assets_frontend': [
            'saudi_muqeem_workforce_operations/static/src/css/compliance_portal.css',
        ],
    },

    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 99.00,
    'currency': 'USD',
}
