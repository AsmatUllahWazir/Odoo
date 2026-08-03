# -*- coding: utf-8 -*-
{
    'name': 'Agriculture & Farm Management Suite',
    'version': '17.0.1.0.0',
    'category': 'Agriculture',
    'summary': 'Complete farm management: crops, seasons, inputs, harvest, equipment, and P&L tracking.',
    'description': """
Agriculture & Farm Management Suite
=====================================
A comprehensive, production-ready Odoo module for commercial agriculture operations.

**Key Features:**
- **Field & Parcel Management**: GIS coordinates, soil type, acreage tracking
- **Crop & Season Planning**: Planting schedules, expected vs actual yields, budget tracking
- **Input Applications**: Fertilizer, pesticide, irrigation with lot traceability
- **Harvest Management**: Yield recording, quality grading, lot linking to inventory
- **Weather Integration**: API hooks for weather logging and crop correlation
- **Disease & Pest Tracking**: Incident logs, treatment history, economic impact
- **Equipment Management**: Farm machinery linked to maintenance schedules
- **Seasonal P&L**: Automatic profit/loss per crop, field, and season
- **Traceability**: Full chain from input application → cultivation → harvest → sale
- **Multi-Company**: Full multi-company and multi-location support

**Integrations:**
- Inventory (stock moves, lots, packages)
- Purchase (input procurement)
- Accounting (seasonal P&L, equipment depreciation)
- Maintenance (farm machinery service schedules)
- Website Portal (customer traceability queries)

**Target Industries:**
- Commercial crop farms
- Agricultural cooperatives
- Plantation management
- Seed production companies
- Agri-trading and export firms

For Odoo Community & Enterprise Editions.
    """,
    'author': 'Wazirz',
    'website': '',
    'license': 'OPL-1',
    'price': 39.00,
    'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'stock',
        'purchase',
        'account',
        'maintenance',
        'web',
        'portal',
    ],
    'data': [
        'security/farm_security.xml',
        'security/ir.model.access.csv',
        'data/farm_sequence.xml',
        'data/farm_crop_data.xml',
        'wizard/farm_harvest_wizard_views.xml',
        'views/farm_field_views.xml',
        'views/farm_crop_views.xml',
        'views/farm_season_views.xml',
        'views/farm_cultivation_views.xml',
        'views/farm_input_application_views.xml',
        'views/farm_harvest_views.xml',
        'views/farm_weather_views.xml',
        'views/farm_disease_pest_views.xml',
        'views/farm_equipment_views.xml',
        'views/farm_dashboard.xml',
        'views/res_config_settings_views.xml',
        'views/farm_menus.xml',
        'reports/farm_reports.xml',
        'reports/farm_season_report_templates.xml',
    ],
    'demo': [
        'data/farm_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'agriculture_management/static/src/css/dashboard.css',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
