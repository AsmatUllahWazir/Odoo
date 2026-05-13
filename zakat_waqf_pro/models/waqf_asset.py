# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class WaqfAsset(models.Model):
    _name = 'waqf.asset'
    _description = 'Waqf Endowment Asset'
    _rec_name = 'name'
    _order = 'acquisition_date desc, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Asset Name', required=True, tracking=True)

    asset_code = fields.Char(
        string='Asset Code',
        default=lambda self: self.env['ir.sequence'].next_by_code('waqf.asset'),
        readonly=True,
        copy=False
    )

    asset_type = fields.Selection([
        ('land', 'Land'),
        ('building', 'Building'),
        ('equipment', 'Equipment'),
        ('vehicle', 'Vehicle'),
        ('cash', 'Cash Waqf'),
        ('other', 'Other'),
    ], required=True, tracking=True)

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        readonly=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

    # Valuation Fields
    initial_value = fields.Monetary(string='Initial Value', required=True, tracking=True)
    depreciation_rate = fields.Float(string='Annual Depreciation %', default=5.0, tracking=True)
    salvage_value = fields.Monetary(string='Salvage Value', default=0.0)

    current_value = fields.Monetary(
        string='Current Value',
        compute='_compute_current_value',
        store=True,
        tracking=True
    )

    total_depreciation = fields.Monetary(
        string='Total Depreciation',
        compute='_compute_current_value',
        store=True
    )

    # Income Fields
    annual_income = fields.Monetary(string='Annual Income', default=0.0, tracking=True)
    allocation_percent = fields.Float(string='Charity Allocation %', default=70.0, tracking=True)
    charity_amount = fields.Monetary(
        string='Annual Charity Amount',
        compute='_compute_charity_amount',
        store=True
    )

    # Dates
    acquisition_date = fields.Date(string='Acquisition Date', required=True, tracking=True)
    depreciation_months = fields.Integer(
        string='Depreciation Months',
        compute='_compute_depreciation_months',
        store=True
    )

    # Beneficiaries
    waqf_beneficiary_ids = fields.Many2many(
        'res.partner',
        string='Beneficiaries',
        help='Organizations or individuals who benefit from this Waqf'
    )

    # Status
    state = fields.Selection([
        ('active', 'Active'),
        ('depreciated', 'Fully Depreciated'),
        ('sold', 'Sold'),
        ('under_maintenance', 'Under Maintenance'),
    ], default='active', tracking=True)

    description = fields.Text(string='Description')

    # Compute Methods
    @api.depends('initial_value', 'depreciation_rate', 'acquisition_date', 'salvage_value')
    def _compute_current_value(self):
        for rec in self:
            if rec.acquisition_date and rec.initial_value > 0:
                days_since_acquisition = (date.today() - rec.acquisition_date).days
                years = days_since_acquisition / 365.25
                depreciation_amount = rec.initial_value * (rec.depreciation_rate / 100) * years

                # Cap at initial value minus salvage value
                max_depreciation = rec.initial_value - rec.salvage_value
                if depreciation_amount > max_depreciation:
                    depreciation_amount = max_depreciation

                rec.total_depreciation = depreciation_amount
                rec.current_value = rec.initial_value - depreciation_amount
            else:
                rec.current_value = rec.initial_value
                rec.total_depreciation = 0.0

    @api.depends('acquisition_date')
    def _compute_depreciation_months(self):
        for rec in self:
            if rec.acquisition_date:
                months = (date.today().year - rec.acquisition_date.year) * 12 + (
                            date.today().month - rec.acquisition_date.month)
                rec.depreciation_months = max(0, months)
            else:
                rec.depreciation_months = 0

    @api.depends('annual_income', 'allocation_percent')
    def _compute_charity_amount(self):
        for rec in self:
            rec.charity_amount = rec.annual_income * (rec.allocation_percent / 100)

    # Action Methods
    def action_compute_charity(self):
        """Create charity income record"""
        for rec in self:
            if rec.charity_amount > 0 and rec.waqf_beneficiary_ids:
                # Create a note in chatter
                beneficiary_names = ', '.join(rec.waqf_beneficiary_ids.mapped('name'))
                message = f"Charity Income: {rec.charity_amount:,.2f} {rec.currency_id.symbol or 'SAR'} allocated to {beneficiary_names}"
                rec.message_post(body=message)

                # Optionally create an accounting entry
                # This can be extended to create journal entries

    def action_create_zakat_calculation(self):
        """Create a Zakat calculation from this Waqf asset's charity amount"""
        self.ensure_one()
        if self.charity_amount > 0:
            calculation = self.env['zakat.calculation'].create({
                'partner_id': self.waqf_beneficiary_ids[0].id if self.waqf_beneficiary_ids else False,
                'other_assets': self.charity_amount,
                'notes': f"From Waqf Asset: {self.name}",
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'zakat.calculation',
                'res_id': calculation.id,
                'view_mode': 'form',
            }

    def action_sell_asset(self):
        """Mark asset as sold"""
        for rec in self:
            rec.state = 'sold'

    # Validation
    @api.constrains('depreciation_rate')
    def _check_depreciation_rate(self):
        for rec in self:
            if rec.depreciation_rate < 0 or rec.depreciation_rate > 100:
                raise ValidationError(_("Depreciation rate must be between 0 and 100 percent."))

    @api.constrains('allocation_percent')
    def _check_allocation_percent(self):
        for rec in self:
            if rec.allocation_percent < 0 or rec.allocation_percent > 100:
                raise ValidationError(_("Allocation percentage must be between 0 and 100."))
