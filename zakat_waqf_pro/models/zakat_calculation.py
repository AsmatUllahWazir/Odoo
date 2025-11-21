from odoo import models, fields, api
from odoo.exceptions import UserError

NISAB_GOLD = 85
GOLD_PRICE = 250


class ZakatCalculation(models.Model):
    _name = 'zakat.calculation'
    _description = 'Zakat Calculation'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    calculation_date = fields.Date(default=fields.Date.today, string='Calculation Date')
    school = fields.Selection([
        ('hanafi', 'Hanafi'),
        ('shafii', 'Shafi’i'),
    ], default='hanafi', string='Madhhab/School')
    nisab_threshold = fields.Monetary(string='Nisab Threshold', compute='_compute_nisab')
    total_wealth = fields.Monetary(string='Total Wealth', compute='_compute_total_wealth')
    zakat_due = fields.Monetary(string='Zakat Due (2.5%)', compute='_compute_zakat_due')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    cash_amount = fields.Monetary(string='Cash & Bank')
    inventory_value = fields.Monetary(string='Inventory Value')
    receivables = fields.Monetary(string='Receivables')
    gold_silver = fields.Monetary(string='Gold/Silver')
    other_assets = fields.Monetary(string='Other Assets')

    sadad_bill_id = fields.Many2one('account.move', string='SADAD Bill')
    certificate_id = fields.Many2one('zakat.certificate', string='Certificate')

    @api.depends('cash_amount', 'inventory_value', 'receivables', 'gold_silver', 'other_assets')
    def _compute_total_wealth(self):
        for rec in self:
            rec.total_wealth = rec.cash_amount + rec.inventory_value + rec.receivables + rec.gold_silver + rec.other_assets

    @api.depends('school')
    def _compute_nisab(self):
        for rec in self:
            nisab = NISAB_GOLD * GOLD_PRICE
            if rec.school == 'shafii':
                nisab *= 0.95
            rec.nisab_threshold = nisab

    @api.depends('total_wealth', 'nisab_threshold')
    def _compute_zakat_due(self):
        for rec in self:
            if rec.total_wealth >= rec.nisab_threshold:
                rec.zakat_due = rec.total_wealth * 0.025
            else:
                rec.zakat_due = 0

    @api.model
    def auto_calculate_from_assets(self):
        partners = self.env['res.partner'].search([('is_company', '=', False)])
        for partner in partners:
            cash = sum(self.env['account.move.line'].search(
                [('partner_id', '=', partner.id), ('account_id.internal_type', '=', 'liquidity')]).mapped(
                'debit')) - sum(...['credit'])
            inventory = sum(
                self.env['stock.quant'].search([('owner_id', '=', partner.id)]).mapped('quantity') * self.env[
                    'product.product'].mapped('standard_price'))
            self.create({
                'partner_id': partner.id,
                'cash_amount': cash,
                'inventory_value': inventory,
            })

    def action_generate_sadad_bill(self):
        self.ensure_one()
        if not self.zakat_due:
            raise UserError("No Zakat due to generate bill.")

        account_id = self.env['ir.config_parameter'].sudo().get_param(
            'zakat_waqf_pro.default_zakat_income_account'
        )
        if not account_id:
            raise UserError("Default Zakat Income Account not set.")

        income_account = self.env['account.account'].browse(int(account_id))

        if not income_account.exists():
            raise UserError("Income account not found.")

        product_category = self.env.ref('product.product_category_all')

        product = self.env['product.product'].create({
            'name': 'Zakat Payment Service',
            'type': 'service',
            'categ_id': product_category.id,
            'list_price': self.zakat_due,
            'property_account_income_id': income_account.id,
        })

        # CREATE INVOICE
        bill = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 1.0,
                'price_unit': self.zakat_due,
                'name': f"Zakat Payment - {self.partner_id.name}",
            })],
        })

        self.sadad_bill_id = bill.id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_generate_certificate(self):
        self.ensure_one()
        wizard = self.env['zakat.certificate.wizard'].create({
            'calculation_id': self.id
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'zakat.certificate.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
