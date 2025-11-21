{
    'name': 'ZakatPro: Zakat & Waqf Management',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Islamic Finance',
    'summary': 'Islamic Zakat Calculation & Waqf Asset Tracking with SADAD Integration',
    'description': """
        ZakatPro: First Odoo Module for Islamic Charity Management
        - Auto Zakat on Assets (Cash, Inventory, Receivables) - Hanafi/Shafi’i
        - Waqf Endowments: Track Land/Buildings, Depreciation, Income Distribution
        - Generate Zakat Certificates (PDF/QR)
        - SADAD Payment Bills for ZATCA
        - Hijri Reports + Arabic UI
        
        Perfect for companies in KSA, UAE, Qatar, Kuwait, Bahrain, Oman
        
    """,

    'author': 'Wazirz',
    'website': '',
    'support': 'wazirfreelancer@gmail.com',
    'license': 'OPL-1',
    'price': 19.00,
    'currency': 'USD',

    'depends': ['account', 'hr', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/zakat_sequence.xml',
        'views/zakat_calculation_views.xml',
        'views/waqf_asset_views.xml',
        'wizards/zakat_certificate_wizard.xml',
        'reports/zakat_certificate_report.xml',
        'reports/zakat_certificate_template.xml',
    ],

    'images': [
        'static/description/icon.png',
        'static/description/screenshot_1_form.png',
        'static/description/screenshot_2_summary.png',
        'static/description/screenshot_3_invoice.jpg',
        'static/description/screenshot_4_certificate.png',
        'static/description/screenshot_5_certificate_closeup.png',
        'static/description/screenshot_6_menu.jpg',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
