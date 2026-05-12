# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    gold_price_per_gram = fields.Float(
        string='Gold Price (SAR/gram)',
        config_parameter='zakat_waqf_pro.gold_price',
        default=250.0,
        help='Current price of 1 gram of gold in Saudi Riyals. Used to calculate Nisab threshold (85g of gold).'
    )

    zakat_income_account_id = fields.Many2one(
        'account.account',
        string='Default Zakat Income Account',
        config_parameter='zakat_waqf_pro.zakat_income_account',
        domain="[('account_type', '=', 'income'), ('company_id', '=', company_id)]",
        help='Default income account for Zakat invoices'
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    enable_auto_fetch = fields.Boolean(
        string='Auto-fetch from Accounting',
        config_parameter='zakat_waqf_pro.enable_auto_fetch',
        default=True,
        help='Automatically fetch cash and receivable balances from accounting data'
    )

    default_school = fields.Selection([
        ('hanafi', 'Hanafi'),
        ('shafii', 'Shafi\'i'),
        ('maliki', 'Maliki'),
        ('hanbali', 'Hanbali'),
    ], string='Default Madhhab', config_parameter='zakat_waqf_pro.default_school', default='hanafi')
