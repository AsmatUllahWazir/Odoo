# -*- coding: utf-8 -*-

from . import models
from . import wizard


def post_init_hook(env):
    """Post-installation hook to set up initial configuration"""
    # Create HUB company if it doesn't exist
    hub_company = env['res.company'].search([('name', '=', 'HUB - OCR Processing Center')], limit=1)
    if not hub_company:
        hub_company = env['res.company'].create({
            'name': 'HUB - OCR Processing Center',
            'currency_id': env.ref('base.EUR').id,
            'email': 'hub@company.com',
        })

    # Set HUB company in config
    config = env['vendor.bill.dispatch.config'].search([], limit=1)
    if not config:
        config = env['vendor.bill.dispatch.config'].create({
            'hub_company_id': hub_company.id,
            'finance_approval_threshold': 5000.0,
            'auto_ocr_on_upload': True,
            'enable_email_reception': True,
        })

    # Create default email alias for bill reception
    alias = env['mail.alias'].search([('alias_name', '=', 'vendor.bills')], limit=1)
    if not alias:
        env['mail.alias'].create({
            'alias_name': 'vendor.bills',
            'alias_model_id': env.ref('account.model_account_move').id,
            'alias_contact': 'everyone',
            'alias_defaults': "{'move_type': 'in_invoice', 'dispatch_state': 'ocr_draft'}",
        })