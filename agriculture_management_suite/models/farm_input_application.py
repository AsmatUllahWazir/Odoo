# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FarmInputApplication(models.Model):
    _name = 'farm.input.application'
    _description = 'Farm Input Application'
    _inherit = ['mail.thread']
    _order = 'application_date desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company)

    # Classification
    input_type = fields.Selection([
        ('fertilizer', 'Fertilizer'),
        ('pesticide', 'Pesticide/Herbicide'),
        ('fungicide', 'Fungicide'),
        ('irrigation', 'Irrigation/Water'),
        ('seed', 'Seed/Treatment'),
        ('soil_amendment', 'Soil Amendment'),
        ('growth_regulator', 'Growth Regulator'),
        ('other', 'Other'),
    ], string='Input Type', required=True, tracking=True)

    application_date = fields.Date(string='Application Date', required=True, default=fields.Date.today, tracking=True)
    application_method = fields.Selection([
        ('broadcast', 'Broadcast'),
        ('fertigation', 'Fertigation'),
        ('foliar', 'Foliar Spray'),
        ('soil_drench', 'Soil Drench'),
        ('injection', 'Injection'),
        ('manual', 'Manual/Hand'),
        ('mechanical', 'Mechanical'),
        ('aerial', 'Aerial'),
    ], string='Application Method', tracking=True)

    # Relations
    season_id = fields.Many2one('farm.season', string='Season', required=True)
    cultivation_id = fields.Many2one('farm.cultivation', string='Cultivation',
                                      domain="[('season_id', '=', season_id)]")
    field_id = fields.Many2one('farm.field', string='Field', required=True)

    # Product & Quantity
    product_id = fields.Many2one('product.product', string='Input Product', required=True,
                                  domain="[('type', 'in', ['product', 'consu'])]")
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number',
                              domain="[('product_id', '=', product_id)]",
                              help='Lot number for traceability')
    quantity = fields.Float(string='Quantity Applied', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', store=True)
    area_covered = fields.Float(string='Area Covered (ha)', help='Area covered by this application')

    # Weather at application
    weather_condition = fields.Selection([
        ('sunny', 'Sunny'),
        ('cloudy', 'Cloudy'),
        ('rainy', 'Rainy'),
        ('windy', 'Windy'),
        ('humid', 'Humid'),
    ], string='Weather Condition')
    temperature_c = fields.Float(string='Temperature (°C)')
    wind_speed = fields.Float(string='Wind Speed (km/h)')

    # Costing
    unit_cost = fields.Float(string='Unit Cost', compute='_compute_cost', store=True, readonly=False)
    total_cost = fields.Float(string='Total Cost', compute='_compute_cost', store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)

    # Compliance & Safety
    phi_days = fields.Integer(string='Pre-Harvest Interval (days)',
                               help='Days before harvest when this input was last applied')
    reentry_hours = fields.Integer(string='Re-entry Interval (hours)')
    safety_equipment_used = fields.Boolean(string='Safety Equipment Used', default=False)
    compliance_notes = fields.Text(string='Compliance Notes')

    # Stock Integration
    stock_move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True, copy=False,
                                     help='Linked stock consumption move')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('farm.input') or 'New'
        return super(FarmInputApplication, self).create(vals_list)

    @api.depends('product_id', 'quantity')
    def _compute_cost(self):
        for app in self:
            if app.product_id:
                app.unit_cost = app.product_id.standard_price or 0
                app.total_cost = app.unit_cost * app.quantity
            else:
                app.unit_cost = 0
                app.total_cost = 0

    @api.constrains('application_date', 'cultivation_id')
    def _check_phi(self):
        for app in self:
            if app.cultivation_id and app.cultivation_id.actual_harvest_date:
                if app.application_date and app.application_date > app.cultivation_id.actual_harvest_date:
                    raise ValidationError(_('Input application date cannot be after harvest date.'))

    def action_create_stock_move(self):
        """Create a stock move to consume the input from farm location."""
        self.ensure_one()
        if not self.field_id.farm_location_id:
            raise ValidationError(_('Please set a farm location on the field first.'))

        move_vals = {
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.uom_id.id,
            'location_id': self.field_id.farm_location_id.id,
            'location_dest_id': self.env.ref('stock.location_production').id,
            'name': _('Farm Input: %s') % self.name,
            'origin': self.name,
        }
        move = self.env['stock.move'].create(move_vals)
        move._action_confirm()
        move._action_done()
        self.stock_move_id = move.id
        return True
