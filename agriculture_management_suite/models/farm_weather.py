# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FarmWeatherLog(models.Model):
    _name = 'farm.weather.log'
    _description = 'Weather Log'
    _order = 'date desc'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company)
    field_id = fields.Many2one('farm.field', string='Field')
    season_id = fields.Many2one('farm.season', string='Season')

    # Weather Data
    source = fields.Selection([
        ('manual', 'Manual Entry'),
        ('api', 'Weather API'),
        ('station', 'Weather Station'),
    ], string='Data Source', default='manual')

    temperature_max = fields.Float(string='Max Temperature (°C)')
    temperature_min = fields.Float(string='Min Temperature (°C)')
    temperature_avg = fields.Float(string='Avg Temperature (°C)', compute='_compute_avg_temp', store=True)
    humidity_percent = fields.Float(string='Humidity %')
    precipitation_mm = fields.Float(string='Precipitation (mm)')
    wind_speed = fields.Float(string='Wind Speed (km/h)')
    wind_direction = fields.Char(string='Wind Direction')
    sunshine_hours = fields.Float(string='Sunshine Hours')
    uv_index = fields.Float(string='UV Index')
    pressure_hpa = fields.Float(string='Pressure (hPa)')

    # Impact
    crop_impact = fields.Selection([
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
        ('severe', 'Severe Damage'),
    ], string='Crop Impact', default='neutral')
    impact_notes = fields.Text(string='Impact Notes')

    @api.depends('date', 'field_id')
    def _compute_name(self):
        for log in self:
            field_name = log.field_id.name if log.field_id else 'General'
            log.name = _('%s - %s') % (field_name, log.date)

    @api.depends('temperature_max', 'temperature_min')
    def _compute_avg_temp(self):
        for log in self:
            if log.temperature_max and log.temperature_min:
                log.temperature_avg = (log.temperature_max + log.temperature_min) / 2
            else:
                log.temperature_avg = log.temperature_max or log.temperature_min or 0

    def action_fetch_weather_api(self):
        """Hook for weather API integration. To be extended with actual API calls."""
        self.ensure_one()
        # Placeholder: In production, integrate with OpenWeatherMap, WeatherAPI, etc.
        # api_key = self.env['ir.config_parameter'].sudo().get_param('agriculture.weather_api_key')
        # Make API call and populate fields
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Weather API'),
                'message': _('Weather API integration hook. Configure API key in Settings.'),
                'type': 'info',
            }
        }
