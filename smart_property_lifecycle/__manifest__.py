{
    'name': 'Smart Property Lifecycle Suite',
    'version': '17.0.1.0.0',
    'category': 'Real Estate',
    'summary': 'Complete property lifecycle management for real estate agencies',
    'description': """
        Smart Property Lifecycle Suite
        ==============================

        Comprehensive property management solution covering:
        * Property listing and marketing
        * Viewing and tenant screening
        * Lease management with e-signature
        * Occupancy and maintenance tracking
        * HOA/Condo association management
        * Dynamic pricing and market analytics
        * IoT device integration placeholders
        * AR/Virtual tour support
        * Tenant portal with self-service
        * Portfolio analytics and reporting

        Full lifecycle: Listing → Marketing → Viewing → Tenant Screening → 
        Leasing → Occupancy/Maintenance → Renewal/Termination → Portfolio Analytics
    """,
    'author': 'Property Management Solutions',
    'website': 'https://www.example.com',
    'depends': [
        'base',
        'contacts',
        'sale',
        'account',
        'project',
        'maintenance',
        'website',
        'portal',
        # 'sign',
        'mail',
        'calendar',
        'web',
        'base_automation',
    ],

    'external_dependencies': {
        'python': [],
    },

    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',

        # Data
        'data/sequence_data.xml',
        'data/email_template_data.xml',
        'data/demo_properties.xml',
        'data/demo_leases.xml',
        'data/demo_maintenance.xml',

        # Views
        'views/property_unit_views.xml',
        'views/property_property_views.xml',
        'views/property_lease_views.xml',
        'views/property_viewing_views.xml',
        'views/property_maintenance_views.xml',
        'views/property_tenant_screening_views.xml',
        'views/property_hoa_views.xml',
        'views/property_dynamic_pricing_views.xml',
        'views/property_portfolio_views.xml',
        'views/property_iot_views.xml',

        # Templates
        'views/website_property_templates.xml',
        'views/website_portal_templates.xml',

        # Menus
        'views/property_menus.xml',

        # Reports
        'reports/property_lease_report.xml',
        # 'reports/property_portfolio_report.xml',

        # Wizards
        'wizards/property_lease_wizard_views.xml',
        'wizards/property_screening_wizard_views.xml',
        'wizards/property_renewal_wizard_views.xml',

        # Email Templates
        'data/email_template_data.xml',

        # Cron Jobs
        'data/cron_data.xml',
    ],
    'demo': [
        'data/demo_properties.xml',
        'data/demo_leases.xml',
        'data/demo_maintenance.xml',
    ],
    'qweb': [
        'static/src/xml/property_kanban.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'smart_property_lifecycle/static/src/js/property_dashboard.js',
            'smart_property_lifecycle/static/src/js/property_iot.js',
            'smart_property_lifecycle/static/src/css/property_style.css',
        ],
        'web.assets_frontend': [
            'smart_property_lifecycle/static/src/css/website_property.css',
            'smart_property_lifecycle/static/src/js/website_property.js',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}
