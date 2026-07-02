# -*- coding: utf-8 -*-
###############################################################################
# Module: Employee Activity Tracker & Monitor
# Version: 17.0.1.0.0
# Author: Custom Development
# Description:
#   Complete advanced employee activity tracking and monitoring system for Odoo.
#   Tracks sessions, actions, field changes, button clicks, and provides a
#   real-time CEO/admin dashboard with analytics and reporting.
#
# Compatible: Odoo 17, 18, 19
###############################################################################
{
    'name': 'Employee Activity Tracker & Monitor',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Tracking',
    'summary': 'Complete real-time employee activity tracking, session monitoring, '
               'audit logs, field change history, and CEO dashboard.',
    'description': """
        Employee Activity Tracker & Monitor
        ====================================
        Track every user action inside Odoo from login to logout.

        Key Features:
        - Real-time session tracking (login/logout, duration, IP, browser)
        - Full activity log across all installed modules
        - Field-level change tracking (old value → new value)
        - Button click tracking
        - User activity timeline
        - CEO/Admin live monitoring dashboard
        - Smart status indicators (Green/Red/Yellow/Gray)
        - Daily/Weekly/Monthly reports via email
        - Suspicious activity alerts
        - Multi-company support
        - Async background logging for zero performance impact
    """,
    'author': 'Wazirz',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'hr',
        'base_setup',
        'base_automation',
    ],
    'data': [
        # # Security
        'security/activity_tracker_groups.xml',
        # 'security/activity_tracker_rules.xml',
        'security/ir.model.access.csv',
        #
        # # Data
        'data/cron_jobs.xml',
        'data/email_templates.xml',
        # 'data/tracker_config.xml',
        #
        # # Views - Models
        'views/session_log_views.xml',
        'views/activity_log_views.xml',
        'views/field_change_log_views.xml',
        'views/button_click_log_views.xml',
        # 'views/security_log_views.xml',
        # 'views/access_log_views.xml',
        # 'views/tracker_dashboard_views.xml',
        # 'views/tracker_config_views.xml',
        'views/user_timeline_views.xml',
        #
        # # Menus
        'views/menu_views.xml',
    ],
    'assets': {
        # 'web.assets_backend': [
        #     'employee_activity_tracker/static/src/css/tracker_dashboard.css',
        #     'employee_activity_tracker/static/src/js/activity_tracker.js',
        #     'employee_activity_tracker/static/src/js/session_monitor.js',
        #     'employee_activity_tracker/static/src/js/tracker_dashboard.js',
        #     'employee_activity_tracker/static/src/xml/tracker_templates.xml',
        # ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'price': 35.00,
    'currency': 'USD',
}