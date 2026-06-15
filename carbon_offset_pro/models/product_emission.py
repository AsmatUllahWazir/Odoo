from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductEmissionFactor(models.Model):
    _name = 'carbon.offset.product.emission'
    _description = 'Product Carbon Emission Factor'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id', store=True)

    production_emission_kg = fields.Float(string='Production CO2e (kg/unit)', default=0.0)
    packaging_emission_kg = fields.Float(string='Packaging CO2e (kg/unit)', default=0.0)
    weight_kg = fields.Float(string='Weight (kg)', default=0.0)

    transport_mode = fields.Selection([
        ('air', 'Air Freight'),
        ('truck', 'Truck'),
        ('rail', 'Rail'),
        ('sea', 'Sea Freight'),
    ], string='Transport Mode', default='truck')

    renewable_percentage = fields.Float(string='Renewable Energy %', default=0.0)

    total_emission_kg = fields.Float(string='Total CO2e (kg/unit)', compute='_compute_total_emission', store=True)
    carbon_rating = fields.Char(string='Carbon Rating', compute='_compute_carbon_rating', store=True)

    TRANSPORT_FACTORS = {
        'air': 1.5,
        'truck': 0.2,
        'rail': 0.03,
        'sea': 0.015,
    }

    @api.depends('production_emission_kg', 'packaging_emission_kg', 'weight_kg', 'transport_mode', 'renewable_percentage')
    def _compute_total_emission(self):
        for record in self:
            adjusted_production = record.production_emission_kg * (1 - record.renewable_percentage / 100)
            factor = self.TRANSPORT_FACTORS.get(record.transport_mode, 0.2)
            transport = (record.weight_kg * 500 * factor) / 1000
            record.total_emission_kg = adjusted_production + record.packaging_emission_kg + transport

    @api.depends('total_emission_kg')
    def _compute_carbon_rating(self):
        for record in self:
            if record.total_emission_kg <= 0.1:
                record.carbon_rating = 'A++'
            elif record.total_emission_kg <= 0.5:
                record.carbon_rating = 'A'
            elif record.total_emission_kg <= 1.5:
                record.carbon_rating = 'B'
            elif record.total_emission_kg <= 5.0:
                record.carbon_rating = 'C'
            elif record.total_emission_kg <= 15.0:
                record.carbon_rating = 'D'
            else:
                record.carbon_rating = 'E'


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    emission_factor_ids = fields.One2many('carbon.offset.product.emission', 'product_tmpl_id', string='Emission Factors')
    total_product_emission = fields.Float(string='Product CO2e (kg)', compute='_compute_emission_summary')
    carbon_rating = fields.Char(string='Carbon Rating', compute='_compute_emission_summary')

    def _compute_emission_summary(self):
        for product in self:
            factors = product.emission_factor_ids
            if factors:
                product.total_product_emission = sum(factors.mapped('total_emission_kg')) / len(factors)
                ratings = factors.mapped('carbon_rating')
                rating_order = ['A++', 'A', 'B', 'C', 'D', 'E']
                product.carbon_rating = min(ratings, key=lambda r: rating_order.index(r) if r in rating_order else 0) if ratings else ''
            else:
                product.total_product_emission = 0.0
                product.carbon_rating = ''
