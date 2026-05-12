{
    'name': 'ZakatPro: Zakat & Waqf Management',
    'version': '17.0.2.0.0',
    'category': 'Accounting/Islamic Finance',
    'summary': 'Islamic Zakat Calculation & Waqf Asset Tracking with SADAD Integration',
    'description': """
        ZakatPro - Complete Islamic Finance Solution for Odoo 17
        ========================================================
        
        Features:
        ---------
        • Automatic Zakat calculation (2.5% of net wealth)
        • Nisab threshold based on gold price (85g)
        • Supports Hanafi & Shafi'i schools
        • Generate official bilingual certificates (Arabic/English)
        • SADAD-compatible customer invoices
        • Waqf asset tracking with depreciation
        • Charity income distribution to beneficiaries
        • Hijri & Gregorian date support
        • Full Arabic translation
        
        Perfect for companies in:
        - Saudi Arabia (ZATCA ready)
        - United Arab Emirates
        - Egypt
        - Qatar
        - Kuwait
        - Bahrain
        - Oman
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
        'security/zakat_security.xml',
        'data/zakat_sequence.xml',
        'views/zakat_calculation_views.xml',
        'views/waqf_asset_views.xml',
        'views/zakat_certificate_views.xml',
        # 'views/res_config_settings_views.xml',
        'wizards/zakat_certificate_wizard.xml',
        'reports/zakat_certificate_report.xml',
        'reports/zakat_certificate_template.xml',
        'reports/waqf_assets_report_template.xml',
        'reports/zakat_summary_template.xml',
        'views/menu_views.xml',
    ],

        'images': ['static/description/icon.png'],
        # 'static/description/screenshot_1_form.png',
        # 'static/description/screenshot_2_summary.png',
        # 'static/description/screenshot_3_invoice.jpg',
        # 'static/description/screenshot_4_certificate.png',
        # 'static/description/screenshot_5_certificate_closeup.png',
        # 'static/description/screenshot_6_menu.jpg',
    # ],

        'installable': True,
        'application': True,
        'auto_install': False,
}
