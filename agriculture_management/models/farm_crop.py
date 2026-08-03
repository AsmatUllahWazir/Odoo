# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FarmCrop(models.Model):
    _name = 'farm.crop'
    _description = 'Crop Type'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Crop Name', required=True, tracking=True)
    scientific_name = fields.Char(string='Scientific Name')
    active = fields.Boolean(default=True)

    # Classification
    category = fields.Selection([
        ('cereal', 'Cereal'),
        ('legume', 'Legume'),
        ('vegetable', 'Vegetable'),
        ('fruit', 'Fruit'),
        ('oilseed', 'Oilseed'),
        ('fiber', 'Fiber'),
        ('forage', 'Forage'),
        ('industrial', 'Industrial'),
        ('other', 'Other'),
    ], string='Category', required=True, tracking=True)

    # Agronomic Data
    typical_yield_per_ha = fields.Float(string='Typical Yield (kg/ha)', 
                                         help='Average expected yield per hectare under normal conditions')
    growing_period_days = fields.Integer(string='Growing Period (days)',
                                          help='Typical days from planting to harvest')
    planting_season = fields.Selection([
        ('spring', 'Spring'),
        ('summer', 'Summer'),
        ('autumn', 'Autumn/Fall'),
        ('winter', 'Winter'),
        ('year_round', 'Year Round'),
        ('monsoon', 'Monsoon Dependent'),
    ], string='Optimal Planting Season')

    # Economic
    uom_id = fields.Many2one('uom.uom', string='Harvest UoM', 
                              domain=lambda self: [('category_id', '=', self.env.ref('uom.product_uom_categ_kgm').id)],
                              default=lambda self: self.env.ref('uom.product_uom_kgm'))
    sale_price_per_kg = fields.Float(string='Reference Sale Price/kg', 
                                      help='Average market price for budgeting')

    # Inputs
    water_requirement_mm = fields.Float(string='Water Requirement (mm/season)')
    fertilizer_requirement_kg_ha = fields.Float(string='Fertilizer Requirement (kg N/ha)')

    # Relations
    product_tmpl_id = fields.Many2one('product.template', string='Linked Product',
                                       help='Link to inventory product for harvest tracking')
    cultivation_ids = fields.One2many('farm.cultivation', 'crop_id', string='Cultivations')
    cultivation_count = fields.Integer(string='Cultivation Count', compute='_compute_counts')
    total_harvested_qty = fields.Float(string='Total Harvested (kg)', compute='_compute_counts')

    @api.depends('cultivation_ids', 'cultivation_ids.harvest_ids')
    def _compute_counts(self):
        for crop in self:
            crop.cultivation_count = len(crop.cultivation_ids)
            crop.total_harvested_qty = sum(
                h.quantity for c in crop.cultivation_ids for h in c.harvest_ids
            )

    def action_view_cultivations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cultivations'),
            'res_model': 'farm.cultivation',
            'view_mode': 'tree,form',
            'domain': [('crop_id', '=', self.id)],
            'context': {'default_crop_id': self.id},
        }
