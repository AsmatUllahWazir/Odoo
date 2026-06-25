{
    'name': 'Wazirz Parking Management',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Complete parking management solution for buildings and facilities',
    'description': """
Wazirz Parking Management System
================================
A comprehensive solution for managing parking spaces, vehicle access, and client assignments in residential and commercial buildings.

Key Features:
- Manage building floors and parking units
- Client assignment to specific floors
- Vehicle parking request management with multi-step approval workflow
- Support for Normal, Valet, and Valet+ parking types
- Real-time parking capacity monitoring
- Access card management
- Reject and Block functionality with reasons
- Arabic/English license plate support
- Multi-user role-based access control
- Email notifications and activity tracking
    """,
    'author': 'Wazirz',
    'website': 'https://www.wazirz.com',
    'depends': [
        'base',
        'mail',
        'portal',
        'web',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/building_floor_views.xml',
        'views/client_floor_views.xml',
        'views/parking_report_template.xml',
        'views/car_parking_views.xml',
        'views/wizard_views.xml',
        'views/menus.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 99.00,
    'currency': 'USD',
}