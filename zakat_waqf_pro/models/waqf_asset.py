from odoo import models, fields, api

class WaqfAsset(models.Model):
    _name = 'waqf.asset'
    _description = 'Waqf Endowment Asset'

    name = fields.Char(string='Asset Name', required=True)
    asset_type = fields.Selection([
        ('land', 'Land'),
        ('building', 'Building'),
        ('equipment', 'Equipment'),
    ], required=True)
    value = fields.Monetary(string='Initial Value')
    depreciation_rate = fields.Float(string='Annual Depreciation %', default=5.0)
    current_value = fields.Monetary(string='Current Value', compute='_compute_current_value')
    income_per_year = fields.Monetary(string='Annual Income')
    allocation_percent = fields.Float(string='Charity Allocation %', default=70.0)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    acquisition_date = fields.Date(string='Acquisition Date')
    waqf_beneficiary_ids = fields.Many2many('res.partner', string='Beneficiaries')

    @api.depends('value', 'depreciation_rate', 'acquisition_date')
    def _compute_current_value(self):
        for rec in self:
            if rec.acquisition_date:
                years = (fields.Date.today() - rec.acquisition_date).days / 365.25
                rec.current_value = rec.value * (1 - (rec.depreciation_rate / 100) * years)
            else:
                rec.current_value = rec.value

    def compute_charity_income(self):
        for rec in self:
            charity_amount = rec.income_per_year * (rec.allocation_percent / 100)
            zakat_rec = self.env['zakat.calculation'].create({
                'partner_id': rec.waqf_beneficiary_ids[0].id if rec.waqf_beneficiary_ids else False,
                'other_assets': charity_amount,
            })
            rec.message_post(body=f"Charity Income: {charity_amount} SAR allocated.")