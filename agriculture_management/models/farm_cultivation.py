# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FarmCultivation(models.Model):
    _name = 'farm.cultivation'
    _description = 'Crop Cultivation Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'planting_date desc'

    name = fields.Char(string='Cultivation Reference', readonly=True, copy=False, default='New')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company)

    # Core Relations
    season_id = fields.Many2one('farm.season', string='Season', required=True)
    field_id = fields.Many2one('farm.field', string='Field', required=True, tracking=True)
    crop_id = fields.Many2one('farm.crop', string='Crop', required=True, tracking=True)

    # Planting Details
    planting_date = fields.Date(string='Planting Date', required=True, tracking=True)
    expected_harvest_date = fields.Date(string='Expected Harvest Date', compute='_compute_expected_dates', store=True)
    actual_harvest_date = fields.Date(string='Actual Harvest Date', readonly=True)
    planted_area = fields.Float(string='Planted Area (ha)', required=True, tracking=True)
    seed_variety = fields.Char(string='Seed Variety', tracking=True)
    seed_lot_id = fields.Many2one('stock.lot', string='Seed Lot',
                                   domain="[('product_id.categ_id.name', 'ilike', 'seed')]",
                                   help='Lot number of seeds used for traceability')
    seed_quantity_kg = fields.Float(string='Seed Quantity (kg)')

    # Growth Tracking
    state = fields.Selection([
        ('planned', 'Planned'),
        ('planted', 'Planted'),
        ('germination', 'Germination'),
        ('growing', 'Growing/Vegetative'),
        ('flowering', 'Flowering/Reproductive'),
        ('maturity', 'Maturity'),
        ('harvested', 'Harvested'),
        ('failed', 'Failed/Crop Loss'),
    ], string='Growth Stage', default='planned', tracking=True)

    # Yield
    expected_yield_kg = fields.Float(string='Expected Yield (kg)', compute='_compute_expected_yield', store=True)
    actual_yield_kg = fields.Float(string='Actual Yield (kg)', compute='_compute_actual_yield', store=True)
    yield_variance_percent = fields.Float(string='Yield Variance %', compute='_compute_variance', store=True)

    # Financial
    budget_cost = fields.Float(string='Budgeted Cost', help='Estimated total cost for this cultivation')
    actual_cost = fields.Float(string='Actual Cost', compute='_compute_actual_cost', store=True)

    # Relations
    input_ids = fields.One2many('farm.input.application', 'cultivation_id', string='Input Applications')
    harvest_ids = fields.One2many('farm.harvest', 'cultivation_id', string='Harvests')
    disease_ids = fields.One2many('farm.disease.pest', 'cultivation_id', string='Disease/Pest Incidents')

    # Notes
    notes = fields.Html(string='Cultivation Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('farm.cultivation') or 'New'
        return super(FarmCultivation, self).create(vals_list)

    @api.depends('crop_id', 'planted_area')
    def _compute_expected_yield(self):
        for cult in self:
            cult.expected_yield_kg = (cult.crop_id.typical_yield_per_ha or 0) * cult.planted_area

    @api.depends('harvest_ids', 'harvest_ids.quantity')
    def _compute_actual_yield(self):
        for cult in self:
            cult.actual_yield_kg = sum(h.quantity for h in cult.harvest_ids)

    @api.depends('expected_yield_kg', 'actual_yield_kg')
    def _compute_variance(self):
        for cult in self:
            if cult.expected_yield_kg:
                cult.yield_variance_percent = ((cult.actual_yield_kg - cult.expected_yield_kg) / cult.expected_yield_kg) * 100
            else:
                cult.yield_variance_percent = 0

    @api.depends('crop_id', 'planting_date')
    def _compute_expected_dates(self):
        for cult in self:
            if cult.crop_id and cult.crop_id.growing_period_days and cult.planting_date:
                cult.expected_harvest_date = fields.Date.add(cult.planting_date, days=cult.crop_id.growing_period_days)
            else:
                cult.expected_harvest_date = False

    @api.depends('input_ids', 'input_ids.total_cost')
    def _compute_actual_cost(self):
        for cult in self:
            cult.actual_cost = sum(i.total_cost for i in cult.input_ids)

    @api.constrains('planted_area', 'field_id')
    def _check_planted_area(self):
        for cult in self:
            if cult.planted_area > cult.field_id.usable_area:
                raise ValidationError(_('Planted area cannot exceed field usable area (%s ha).') % cult.field_id.usable_area)

    def action_set_planted(self):
        self.write({'state': 'planted'})

    def action_set_growing(self):
        self.write({'state': 'growing'})

    def action_set_harvested(self):
        self.write({'state': 'harvested', 'actual_harvest_date': fields.Date.today()})

    def action_set_failed(self):
        self.write({'state': 'failed'})

    def action_create_harvest(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Record Harvest'),
            'res_model': 'farm.harvest.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_cultivation_id': self.id, 'default_field_id': self.field_id.id},
        }
