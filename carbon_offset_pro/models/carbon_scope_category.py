from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CarbonScope(models.Model):
    _name = 'carbon.scope'
    _description = 'Carbon Scope'
    _order = 'sequence, name'

    name = fields.Char(string='Scope Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, help='e.g., Scope 1, Scope 2, Scope 3')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    is_active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Scope code must be unique!'),
    ]


class CarbonCategory(models.Model):
    _name = 'carbon.category'
    _description = 'Carbon Emission Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True, help='e.g., Stationary Combustion, Fugitive Emissions')
    sequence = fields.Integer(string='Sequence', default=10)
    scope_id = fields.Many2one('carbon.scope', string='Scope', required=True)
    description = fields.Text(string='Description')
    is_active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Category code must be unique!'),
    ]


class CarbonEmissionFactor(models.Model):
    _name = 'carbon.emission.factor'
    _description = 'Carbon Emission Factor'
    _rec_name = 'display_name'

    name = fields.Char(string='Factor Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    category_id = fields.Many2one('carbon.category', string='Category', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True,
                             domain="[('category_id', '=', 'unit')]")
    factor_value = fields.Float(string='Emission Factor (kg CO2e per unit)', required=True)
    source = fields.Char(string='Source', help='e.g., IPCC, EPA, DEFRA')
    valid_from = fields.Date(string='Valid From')
    valid_to = fields.Date(string='Valid To')
    is_default = fields.Boolean(string='Default Factor', default=False)
    is_active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')

    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    @api.depends('name', 'code', 'factor_value', 'uom_id')
    def _compute_display_name(self):
        for factor in self:
            uom_name = factor.uom_id.name if factor.uom_id else ''
            factor.display_name = f"[{factor.code}] {factor.name} - {factor.factor_value} kg CO2e/{uom_name}"

    @api.constrains('factor_value')
    def _check_factor_value(self):
        for factor in self:
            if factor.factor_value <= 0:
                raise ValidationError(_("Emission factor must be greater than 0."))

    def name_get(self):
        result = []
        for factor in self:
            result.append((factor.id, factor.display_name))
        return result
