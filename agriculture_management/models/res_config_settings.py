# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    agriculture_enabled = fields.Boolean(string='Agriculture Management',
                                          config_parameter='agriculture_management.enabled',
                                          default=True)
    weather_api_provider = fields.Selection([
        ('openweathermap', 'OpenWeatherMap'),
        ('weatherapi', 'WeatherAPI'),
        ('custom', 'Custom'),
    ], string='Weather API Provider',
       config_parameter='agriculture.weather_api_provider')
    weather_api_key = fields.Char(string='Weather API Key',
                                   config_parameter='agriculture.weather_api_key')
    default_currency_id = fields.Many2one('res.currency', string='Default Farm Currency',
                                           related='company_id.currency_id', readonly=False)

    # Traceability
    enable_traceability = fields.Boolean(string='Enable Full Traceability',
                                          config_parameter='agriculture.enable_traceability',
                                          help='Generate unique traceability codes for all harvests')

    # Compliance
    enable_phi_tracking = fields.Boolean(string='Enable PHI Tracking',
                                          config_parameter='agriculture.enable_phi_tracking',
                                          help='Track pre-harvest intervals for pesticide applications')

    # Integration
    auto_create_stock_moves = fields.Boolean(string='Auto-Create Stock Moves',
                                              config_parameter='agriculture.auto_stock_moves',
                                              help='Automatically create inventory moves for inputs and harvests')
