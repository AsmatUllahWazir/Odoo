{
    'name': 'Stock Barcode Scanner Pro',
    'version': '17.0.1.0.0',
    'summary': 'Reliable browser-based barcode scanning for stock pickings',
    'description': """
Stock Barcode Scanner Pro
=========================
A browser-based barcode scanning interface for stock operations.

Features:
- Works in any mobile browser (no native app required)
- Scan to increment quantities on picking lines
- Scan to validate pickings
- Unknown barcode detection with clear warnings
- Manual fallback entry
- No dependency on the Odoo mobile app
    """,
    'author': 'Wazirz',
    'website': '',
    'category': 'Inventory/Inventory',
    'license': 'OPL-1',
    'price': 39.00,
    'currency': 'USD',
    'depends': ['stock', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/barcode_scanner_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'stock_barcode_scanner_pro/static/src/lib/html5-qrcode.min.js',
            'stock_barcode_scanner_pro/static/src/css/barcode_scanner.css',
            'stock_barcode_scanner_pro/static/src/js/barcode_scanner.js',
            # 'stock_barcode_scanner_pro/static/src/js/barcode_scanner.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
