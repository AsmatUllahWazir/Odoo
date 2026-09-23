# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dead_stock_days = fields.Integer(
        string='Dead Stock Threshold (Days)',
        config_parameter='smart_inventory_analytics.dead_stock_days',
        default=90,
        help='Number of days without movement after which a product with stock is considered dead stock'
    )
    aging_auto_analysis = fields.Boolean(
        string='Enable Daily Automatic Analysis',
        config_parameter='smart_inventory_analytics.aging_auto_analysis',
        help='If enabled, a daily aging analysis snapshot will be created automatically'
    )
