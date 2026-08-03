# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FarmSeason(models.Model):
    _name = 'farm.season'
    _description = 'Farming Season'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(string='Season Name', required=True, tracking=True)
    code = fields.Char(string='Season Code', readonly=True, copy=False, default='New')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company, tracking=True)

    # Dates
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date', required=True, tracking=True)
    state = fields.Selection([
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('harvesting', 'Harvesting'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='planning', tracking=True)

    # Financial Planning
    budget_total = fields.Float(string='Total Budget', tracking=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)

    # Computed Financials
    actual_cost_total = fields.Monetary(string='Actual Costs', compute='_compute_financials', store=True,
                                         currency_field='currency_id')
    revenue_total = fields.Monetary(string='Total Revenue', compute='_compute_financials', store=True,
                                     currency_field='currency_id')
    profit_loss = fields.Monetary(string='Profit / Loss', compute='_compute_financials', store=True,
                                   currency_field='currency_id')
    profit_loss_percent = fields.Float(string='Margin %', compute='_compute_financials', store=True)

    # Relations
    field_id = fields.Many2one('farm.field', string='Primary Field', required=True, tracking=True)
    crop_id = fields.Many2one('farm.crop', string='Primary Crop', required=True, tracking=True)
    cultivation_ids = fields.One2many('farm.cultivation', 'season_id', string='Cultivations')
    input_ids = fields.One2many('farm.input.application', 'season_id', string='Input Applications')
    harvest_ids = fields.One2many('farm.harvest', 'season_id', string='Harvests')

    # Totals
    total_planted_area = fields.Float(string='Total Planted Area (ha)', compute='_compute_totals', store=True)
    total_harvest_qty = fields.Float(string='Total Harvest (kg)', compute='_compute_totals', store=True)
    avg_yield_per_ha = fields.Float(string='Avg Yield (kg/ha)', compute='_compute_totals', store=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Season code must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('farm.season') or 'New'
        return super(FarmSeason, self).create(vals_list)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for season in self:
            if season.date_end < season.date_start:
                raise ValidationError(_('End date cannot be before start date.'))

    @api.depends('cultivation_ids', 'cultivation_ids.planted_area')
    def _compute_totals(self):
        for season in self:
            season.total_planted_area = sum(c.planted_area for c in season.cultivation_ids)
            season.total_harvest_qty = sum(h.quantity for h in season.harvest_ids)
            season.avg_yield_per_ha = (
                season.total_harvest_qty / season.total_planted_area 
                if season.total_planted_area else 0
            )

    @api.depends('input_ids', 'input_ids.total_cost', 'harvest_ids', 'harvest_ids.total_value')
    def _compute_financials(self):
        for season in self:
            season.actual_cost_total = sum(i.total_cost for i in season.input_ids)
            season.revenue_total = sum(h.total_value for h in season.harvest_ids)
            season.profit_loss = season.revenue_total - season.actual_cost_total
            season.profit_loss_percent = (
                (season.profit_loss / season.revenue_total * 100) if season.revenue_total else 0
            )

    def action_planning(self):
        self.write({'state': 'planning'})

    def action_active(self):
        self.write({'state': 'active'})

    def action_harvesting(self):
        self.write({'state': 'harvesting'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_view_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Season Report'),
            'res_model': 'farm.season',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }
