# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FarmField(models.Model):
    _name = 'farm.field'
    _description = 'Agricultural Field / Parcel'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Field Name', required=True, tracking=True)
    code = fields.Char(string='Field Code', readonly=True, copy=False, default='New')
    active = fields.Boolean(default=True)

    # Location & GIS
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                  default=lambda self: self.env.company, tracking=True)
    farm_location_id = fields.Many2one('stock.location', string='Farm Location',
                                       domain=[('usage', '=', 'internal')],
                                       help='Linked inventory location for this field')
    country_id = fields.Many2one('res.country', related='company_id.country_id', store=True)
    state_id = fields.Many2one('res.country.state', string='State/Province')
    city = fields.Char(string='City/Town')
    address = fields.Text(string='Address')

    # GIS Data
    latitude = fields.Float(string='Latitude', digits=(10, 8), tracking=True)
    longitude = fields.Float(string='Longitude', digits=(11, 8), tracking=True)
    geo_polygon = fields.Text(string='GeoJSON Polygon', 
                              help='GeoJSON representation of field boundaries for GIS mapping')
    elevation = fields.Float(string='Elevation (m)', help='Elevation in meters above sea level')

    # Physical Characteristics
    total_area = fields.Float(string='Total Area (ha)', required=True, tracking=True,
                              help='Total area in hectares')
    usable_area = fields.Float(string='Usable Area (ha)', tracking=True,
                               help='Cultivable area excluding infrastructure')
    soil_type = fields.Selection([
        ('clay', 'Clay'),
        ('sandy', 'Sandy'),
        ('silty', 'Silty'),
        ('loamy', 'Loamy'),
        ('peaty', 'Peaty'),
        ('chalky', 'Chalky'),
        ('other', 'Other'),
    ], string='Soil Type', tracking=True)
    soil_ph = fields.Float(string='Soil pH', digits=(3, 1))
    soil_texture = fields.Char(string='Soil Texture Notes')
    irrigation_available = fields.Boolean(string='Irrigation Available', default=False, tracking=True)
    irrigation_type = fields.Selection([
        ('drip', 'Drip Irrigation'),
        ('sprinkler', 'Sprinkler'),
        ('flood', 'Flood/Furrow'),
        ('pivot', 'Center Pivot'),
        ('manual', 'Manual'),
    ], string='Irrigation Type')

    # Status & Usage
    state = fields.Selection([
        ('fallow', 'Fallow/Resting'),
        ('preparation', 'Preparation'),
        ('active', 'Active/Cultivated'),
        ('harvested', 'Harvested'),
        ('maintenance', 'Under Maintenance'),
    ], string='Status', default='fallow', tracking=True)

    # Computed Fields
    current_crop_id = fields.Many2one('farm.cultivation', string='Current Cultivation',
                                      compute='_compute_current_crop', store=False)
    current_season_id = fields.Many2one('farm.season', related='current_crop_id.season_id', store=False)
    cultivation_count = fields.Integer(string='Total Cultivations', compute='_compute_cultivation_count')
    total_harvested_qty = fields.Float(string='Total Harvest (kg)', compute='_compute_total_harvest')

    # Relations
    cultivation_ids = fields.One2many('farm.cultivation', 'field_id', string='Cultivations')
    season_ids = fields.One2many('farm.season', 'field_id', string='Seasons')

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Field code must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('farm.field') or 'New'
        return super(FarmField, self).create(vals_list)

    @api.depends('cultivation_ids', 'cultivation_ids.state')
    def _compute_current_crop(self):
        for field in self:
            active = field.cultivation_ids.filtered(lambda c: c.state in ['planted', 'growing', 'flowering'])
            field.current_crop_id = active[:1] if active else False

    @api.depends('cultivation_ids')
    def _compute_cultivation_count(self):
        for field in self:
            field.cultivation_count = len(field.cultivation_ids)

    @api.depends('cultivation_ids', 'cultivation_ids.harvest_ids', 'cultivation_ids.harvest_ids.quantity')
    def _compute_total_harvest(self):
        for field in self:
            field.total_harvested_qty = sum(
                h.quantity for c in field.cultivation_ids for h in c.harvest_ids
            )

    @api.constrains('usable_area', 'total_area')
    def _check_area(self):
        for field in self:
            if field.usable_area and field.usable_area > field.total_area:
                raise ValidationError(_('Usable area cannot exceed total area.'))

    def action_view_cultivations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cultivations'),
            'res_model': 'farm.cultivation',
            'view_mode': 'tree,form',
            'domain': [('field_id', '=', self.id)],
            'context': {'default_field_id': self.id},
        }

    def action_view_harvests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Harvests'),
            'res_model': 'farm.harvest',
            'view_mode': 'tree,form',
            'domain': [('cultivation_id.field_id', '=', self.id)],
        }
