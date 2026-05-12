# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
import logging

_logger = logging.getLogger(__name__)

# Constants
NISAB_GOLD_GRAMS = 85
DEFAULT_GOLD_PRICE = 250  # SAR per gram


class ZakatCalculation(models.Model):
    _name = 'zakat.calculation'
    _description = 'Zakat Calculation'
    _rec_name = 'display_name'
    _order = 'calculation_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Fields
    name = fields.Char(
        string='Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('zakat.calculation'),
        readonly=True,
        copy=False
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        tracking=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        readonly=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

    # Date Fields
    calculation_date = fields.Date(
        default=fields.Date.today,
        string='Calculation Date',
        required=True,
        tracking=True
    )

    hijri_date = fields.Char(
        string='Hijri Date',
        compute='_compute_hijri_date',
        store=True
    )

    # Settings
    school = fields.Selection([
        ('hanafi', 'Hanafi'),
        ('shafii', 'Shafi\'i'),
        ('maliki', 'Maliki'),
        ('hanbali', 'Hanbali'),
    ], default='hanafi', string='Madhhab/School', required=True, tracking=True)

    # Asset Fields
    cash_amount = fields.Monetary(string='Cash & Bank', default=0.0)
    inventory_value = fields.Monetary(string='Inventory Value', default=0.0)
    receivables = fields.Monetary(string='Receivables', default=0.0)
    gold_silver = fields.Monetary(string='Gold/Silver', default=0.0)
    other_assets = fields.Monetary(string='Other Assets', default=0.0)

    # Liabilities (to subtract if needed)
    total_liabilities = fields.Monetary(string='Total Liabilities', default=0.0)

    # Computed Fields
    total_wealth = fields.Monetary(
        string='Total Wealth',
        compute='_compute_total_wealth',
        store=True,
        tracking=True
    )

    net_wealth = fields.Monetary(
        string='Net Wealth (after liabilities)',
        compute='_compute_total_wealth',
        store=True
    )

    gold_price_per_gram = fields.Float(
        string='Gold Price (SAR/gram)',
        compute='_compute_gold_price',
        store=False
    )

    nisab_threshold = fields.Monetary(
        string='Nisab Threshold',
        compute='_compute_nisab',
        store=True
    )

    zakat_due = fields.Monetary(
        string='Zakat Due (2.5%)',
        compute='_compute_zakat_due',
        store=True,
        tracking=True
    )

    is_above_nisab = fields.Boolean(
        string='Above Nisab',
        compute='_compute_zakat_due',
        store=True
    )

    # Related Records
    sadad_bill_id = fields.Many2one('account.move', string='SADAD Bill', readonly=True)
    certificate_ids = fields.One2many('zakat.certificate', 'calculation_id', string='Certificates')

    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('invoiced', 'Invoiced'),
        ('certified', 'Certified'),
        ('paid', 'Paid'),
    ], default='draft', tracking=True)

    notes = fields.Text(string='Additional Notes')

    # Compute Methods
    @api.depends('partner_id', 'calculation_date')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.partner_id.name} - {rec.calculation_date}"

    @api.depends('calculation_date')
    def _compute_hijri_date(self):
        """Convert Gregorian to Hijri date"""
        for rec in self:
            if rec.calculation_date:
                # Simple conversion - for production, use hijri library
                try:
                    from hijri_converter import Hijri, Gregorian
                    hijri = Gregorian(rec.calculation_date.year, rec.calculation_date.month,
                                      rec.calculation_date.day).to_hijri()
                    rec.hijri_date = f"{hijri.year}/{hijri.month:02d}/{hijri.day:02d}"
                except ImportError:
                    # Fallback if hijri_converter not available
                    rec.hijri_date = rec.calculation_date.strftime("%Y/%m/%d")
            else:
                rec.hijri_date = False

    def _get_gold_price(self):
        """Get current gold price from system parameter"""
        gold_price = float(self.env['ir.config_parameter'].sudo().get_param(
            'zakat_waqf_pro.gold_price', DEFAULT_GOLD_PRICE
        ))
        return gold_price

    @api.depends()
    def _compute_gold_price(self):
        gold_price = self._get_gold_price()
        for rec in self:
            rec.gold_price_per_gram = gold_price

    @api.depends('cash_amount', 'inventory_value', 'receivables', 'gold_silver', 'other_assets', 'total_liabilities')
    def _compute_total_wealth(self):
        for rec in self:
            rec.total_wealth = (
                    rec.cash_amount +
                    rec.inventory_value +
                    rec.receivables +
                    rec.gold_silver +
                    rec.other_assets
            )
            rec.net_wealth = rec.total_wealth - rec.total_liabilities

    @api.depends('school')
    def _compute_nisab(self):
        gold_price = self._get_gold_price()
        base_nisab = NISAB_GOLD_GRAMS * gold_price

        for rec in self:
            if rec.school == 'shafii':
                # Shafi'i uses slightly different calculation
                rec.nisab_threshold = base_nisab
            elif rec.school == 'maliki':
                rec.nisab_threshold = base_nisab * 0.98
            elif rec.school == 'hanbali':
                rec.nisab_threshold = base_nisab * 1.02
            else:  # hanafi
                rec.nisab_threshold = base_nisab

    @api.depends('net_wealth', 'nisab_threshold')
    def _compute_zakat_due(self):
        for rec in self:
            if rec.net_wealth >= rec.nisab_threshold:
                rec.zakat_due = rec.net_wealth * 0.025
                rec.is_above_nisab = True
            else:
                rec.zakat_due = 0.0
                rec.is_above_nisab = False

    # Action Methods
    def action_calculate(self):
        """Manually trigger calculation"""
        for rec in self:
            rec._compute_total_wealth()
            rec._compute_nisab()
            rec._compute_zakat_due()
            rec.state = 'calculated'

    def action_generate_sadad_bill(self):
        """Generate SADAD-compatible customer invoice"""
        self.ensure_one()

        if not self.zakat_due or self.zakat_due <= 0:
            raise UserError(_("No Zakat due to generate bill. Zakat Due = %s") % self.zakat_due)

        if self.sadad_bill_id:
            raise UserError(_("A SADAD bill already exists for this calculation."))

        # Get or create Zakat product
        product = self.env['product.product'].search([
            ('name', 'ilike', 'Zakat Payment'),
            ('type', '=', 'service')
        ], limit=1)

        if not product:
            # Get income account from settings
            income_account_id = int(self.env['ir.config_parameter'].sudo().get_param(
                'zakat_waqf_pro.zakat_income_account', 0
            ))

            if not income_account_id:
                # Try to find default income account
                income_account = self.env['account.account'].search([
                    ('account_type', '=', 'income'),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
                income_account_id = income_account.id if income_account else False

            product_category = self.env.ref('product.product_category_all', raise_if_not_found=False)

            product = self.env['product.product'].create({
                'name': 'Zakat Payment Service',
                'type': 'service',
                'categ_id': product_category.id if product_category else False,
                'list_price': self.zakat_due,
                'property_account_income_id': income_account_id,
            })

        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 1.0,
                'price_unit': self.zakat_due,
                'name': f"Zakat Payment - {self.calculation_date} - {self.partner_id.name}",
            })],
            'ref': self.name,
        }

        bill = self.env['account.move'].create(invoice_vals)

        self.write({
            'sadad_bill_id': bill.id,
            'state': 'invoiced'
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_generate_certificate(self):
        """Open wizard to generate certificate"""
        self.ensure_one()

        if not self.zakat_due or self.zakat_due <= 0:
            raise UserError(_("No Zakat due. Cannot generate certificate."))

        wizard = self.env['zakat.certificate.wizard'].create({
            'calculation_id': self.id,
            'recipient_name': self.partner_id.name,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'zakat.certificate.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }

    def action_view_certificates(self):
        """View all certificates for this calculation"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'zakat.certificate',
            'view_mode': 'tree,form',
            'domain': [('calculation_id', '=', self.id)],
            'context': {'default_calculation_id': self.id},
        }

    def action_reset_to_draft(self):
        """Reset calculation to draft"""
        for rec in self:
            rec.state = 'draft'
            rec.sadad_bill_id = False

    @api.model
    def auto_fetch_from_accounting(self):
        """Automatically fetch cash and receivables from accounting"""
        for rec in self.search([('state', '=', 'draft')]):
            partner = rec.partner_id

            # Fetch cash balance from bank accounts
            cash_lines = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('account_id.account_type', 'in', ['asset_cash', 'asset_bank']),
                ('company_id', '=', rec.company_id.id),
                ('full_reconcile_id', '=', False),  # Not reconciled
            ])
            rec.cash_amount = sum(cash_lines.mapped('balance')) * -1 if cash_lines else 0

            # Fetch receivables (accounts receivable)
            receivable_lines = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('account_id.account_type', '=', 'asset_receivable'),
                ('company_id', '=', rec.company_id.id),
                ('balance', '>', 0),
            ])
            rec.receivables = sum(receivable_lines.mapped('balance'))

            rec.action_calculate()

    # Validation
    @api.constrains('cash_amount', 'inventory_value', 'receivables', 'gold_silver', 'other_assets')
    def _check_positive_values(self):
        for rec in self:
            if any(v < 0 for v in
                   [rec.cash_amount, rec.inventory_value, rec.receivables, rec.gold_silver, rec.other_assets]):
                raise ValidationError(_("Asset values cannot be negative."))
