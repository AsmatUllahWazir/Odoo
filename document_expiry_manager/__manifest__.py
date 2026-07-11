# -*- coding: utf-8 -*-
{
    'name': 'Document & License Expiry Tracker',
    'version': '17.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Track expiry of any document (licenses, contracts, certificates, insurance) '
               'attached to any record, with automatic multi-stage reminders and a compliance dashboard.',
    'description': """
Document & License Expiry Tracker
==================================

A universal compliance tool that lets you track the expiry date of **any kind of
document** — driving licenses, passports, insurance policies, contracts,
certifications, work permits, warranties, and more — and attach that document
to **any record in Odoo**: a Contact, an Employee, a Vehicle, an Equipment,
a Project, or any custom model.

Key Features
------------
* Attach an expiry-tracked document to any model/record in the database.
* Configurable document types (Passport, License, Insurance, Contract, etc.).
* Automatic daily check that reclassifies documents as Valid / Expiring Soon / Expired.
* Multi-stage reminder schedule per document (e.g. 30/15/7/1 days before expiry),
  fully configurable, triggering chatter notifications and activities for the
  responsible user so nothing is missed.
* One-click "Open Related Record" smart button to jump straight to the linked record.
* Guided Renewal wizard that updates the expiry date and logs full renewal history
  in the chatter.
* Kanban compliance dashboard grouped by status, Calendar view, and List view with
  color-coded urgency.
* Global default settings (default warning window & reminder schedule) under
  Settings > General Settings.
* Two security groups (User / Manager) with multi-company record rules.
* Zero dependency on HR, Fleet, or any vertical module — works out of the box with
  a stock Odoo install and integrates with any app you already use.

Perfect for HR compliance, fleet management, vendor contract renewals, facility
certifications, insurance tracking, or any scenario where "don't let this expire"
matters.
    """,
    'author': 'Wazirz',
    'website': '',
    'license': 'OPL-1',
    'price': 0.00,
    'currency': 'USD',
    'depends': ['base', 'mail'],
    'data': [
        'security/document_expiry_security.xml',
        'security/ir.model.access.csv',
        'data/document_expiry_data.xml',
        'wizard/document_renew_wizard_views.xml',
        'views/document_expiry_views.xml',
        'views/document_expiry_type_views.xml',
        'views/res_config_settings_views.xml',
        'views/document_expiry_menus.xml',
    ],
    'demo': [
        'data/document_expiry_demo.xml',
    ],
    'images': ['static/description/banner.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
