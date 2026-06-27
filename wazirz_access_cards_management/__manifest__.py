{
    'name': 'Wazirz Access Cards Management',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Complete parking management solution for buildings and facilities',
    'description': """
        Building Management System
        ===========================
        
        A comprehensive solution for managing buildings, floors, clients, 
        access cards, and parking facilities. Perfect for property management 
        companies, building administrators, and facility management firms.
        
        Key Features:
        -------------
        * Client Management - Manage client companies and their contacts
        * Floor Management - Create and manage building floors with capacity limits
        * Access Card Management - Complete lifecycle management of access cards
        * Parking Management - Integration with parking records and spaces
        * Multi-Company Support - Built-in multi-company functionality
        * Email Tracking - Full email and activity tracking on all records
        * Portal Access - Ready for customer portal integration
        * Workflow Management - Complete approval workflow for access cards
        * History Tracking - Track all changes and activities
        
        Workflow:
        ---------
        1. Request → User creates access card request
        2. Management Approval → Manager reviews and approves/rejects
        3. Technical Active → Technical team validates the request
        4. Active → Card is active and ready for use
        5. Block/Unblock → Admins can block/unblock cards as needed
        6. Cancel/Reject → Cards can be cancelled or rejected with reasons
        
        Security Groups:
        ----------------
        * Access Card User - Read-only access to all records
        * Access Card Manager - Full CRUD operations on all records
        * Access Card Administrator - All permissions including configuration
        
        This module provides a complete solution for modern building management
        needs with a focus on usability, security, and scalability.
    """,
    'author': 'Wazirz',
    'website': '',
    'depends': [
        'base',
        'mail',
        'portal',
        'contacts',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        # 'data/access_card_sequence.xml',
        'views/building_floor_views.xml',
        'views/client_floor_views.xml',
        'views/access_card_views.xml',
        'views/reject_reason_wizard_views.xml',
        'views/menus.xml',
    ],

    'images': ['static/description/icon.png'],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 0.00,
    'currency': 'USD',
}