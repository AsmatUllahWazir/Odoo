# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class InventoryAgingAnalysis(models.Model):
    _name = 'inventory.aging.analysis'
    _description = 'Inventory Aging Analysis Snapshot'
    _order = 'analysis_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )
    analysis_date = fields.Date(
        string='Analysis Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)

    line_ids = fields.One2many(
        'inventory.aging.analysis.line',
        'analysis_id',
        string='Aging Lines',
        copy=True,
    )

    # Totals
    total_products = fields.Integer(string='Total Products', compute='_compute_totals', store=True)
    total_dead_stock = fields.Integer(string='Dead Stock Items', compute='_compute_totals', store=True)
    total_value = fields.Monetary(string='Total Stock Value', compute='_compute_totals', store=True, currency_field='currency_id')
    dead_stock_value = fields.Monetary(string='Dead Stock Value', compute='_compute_totals', store=True, currency_field='currency_id')
    high_priority_reorder = fields.Integer(string='High/Critical Reorders', compute='_compute_totals', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)

    # Bucket distribution
    bucket_0_30 = fields.Integer(compute='_compute_totals', store=True)
    bucket_31_60 = fields.Integer(compute='_compute_totals', store=True)
    bucket_61_90 = fields.Integer(compute='_compute_totals', store=True)
    bucket_90_plus = fields.Integer(compute='_compute_totals', store=True)
    bucket_no_move = fields.Integer(compute='_compute_totals', store=True)

    notes = fields.Text(string='Notes')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('inventory.aging.analysis') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids', 'line_ids.is_dead_stock', 'line_ids.stock_value',
                 'line_ids.aging_bucket', 'line_ids.reorder_priority')
    def _compute_totals(self):
        for rec in self:
            lines = rec.line_ids
            rec.total_products = len(lines)
            rec.total_dead_stock = len(lines.filtered('is_dead_stock'))
            rec.total_value = sum(lines.mapped('stock_value'))
            rec.dead_stock_value = sum(lines.filtered('is_dead_stock').mapped('stock_value'))
            rec.high_priority_reorder = len(lines.filtered(
                lambda l: l.reorder_priority in ('high', 'critical')
            ))
            rec.bucket_0_30 = len(lines.filtered(lambda l: l.aging_bucket == '0_30'))
            rec.bucket_31_60 = len(lines.filtered(lambda l: l.aging_bucket == '31_60'))
            rec.bucket_61_90 = len(lines.filtered(lambda l: l.aging_bucket == '61_90'))
            rec.bucket_90_plus = len(lines.filtered(lambda l: l.aging_bucket == '90_plus'))
            rec.bucket_no_move = len(lines.filtered(lambda l: l.aging_bucket == 'no_move'))

    def action_run_analysis(self):
        """Generate a full snapshot of current inventory aging state."""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('This analysis is already done. Reset to draft to re-run.'))

        self.line_ids.unlink()

        domain = [
            ('type', 'in', ['product', 'consu']),
            ('qty_available', '>', 0),
        ]
        # Respect company
        products = self.env['product.product'].with_company(self.company_id).search(domain)

        lines_vals = []
        for product in products:
            # Force recompute of aging fields in case they are stale
            product._compute_aging_fields()
            product._compute_turnover()
            product._compute_reorder_suggestion()

            lines_vals.append({
                'analysis_id': self.id,
                'product_id': product.id,
                'qty_available': product.qty_available,
                'standard_price': product.standard_price,
                'stock_value': product.qty_available * product.standard_price,
                'days_since_last_move': product.days_since_last_move,
                'aging_bucket': product.aging_bucket,
                'is_dead_stock': product.is_dead_stock,
                'dead_stock_score': product.dead_stock_score,
                'turnover_rate_30d': product.turnover_rate_30d,
                'sold_qty_30d': product.sold_qty_30d,
                'suggested_reorder_qty': product.suggested_reorder_qty,
                'reorder_priority': product.reorder_priority,
                'reorder_reason': product.reorder_reason,
            })

        if lines_vals:
            self.env['inventory.aging.analysis.line'].create(lines_vals)

        self.state = 'done'
        self.message_post(body=_('Aging analysis completed. %s products analysed.') % len(lines_vals))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Analysis Complete'),
                'message': _('%s products analysed successfully.') % len(lines_vals),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.model
    def _cron_run_daily_analysis(self):
        """Scheduled action: create and run a daily analysis for each company."""
        companies = self.env['res.company'].search([])
        for company in companies:
            analysis = self.with_company(company).create({
                'analysis_date': fields.Date.context_today(self),
                'company_id': company.id,
                'notes': _('Automatic daily analysis generated by cron'),
            })
            try:
                analysis.action_run_analysis()
                _logger.info('Daily aging analysis %s created for company %s', analysis.name, company.name)
            except Exception as e:
                _logger.exception('Failed to run daily aging analysis for %s: %s', company.name, e)


class InventoryAgingAnalysisLine(models.Model):
    _name = 'inventory.aging.analysis.line'
    _description = 'Inventory Aging Analysis Line'
    _order = 'dead_stock_score desc, stock_value desc'

    analysis_id = fields.Many2one(
        'inventory.aging.analysis',
        string='Analysis',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id',
        string='Product Template',
        store=True,
        index=True,
    )
    default_code = fields.Char(related='product_id.default_code', string='Internal Reference', store=True)
    qty_available = fields.Float(string='Available Qty')
    standard_price = fields.Float(string='Cost')
    stock_value = fields.Float(string='Stock Value')
    days_since_last_move = fields.Integer(string='Days Since Last Move')
    aging_bucket = fields.Selection([
        ('0_30', '0-30 Days'),
        ('31_60', '31-60 Days'),
        ('61_90', '61-90 Days'),
        ('90_plus', '90+ Days'),
        ('no_move', 'No Movement'),
    ], string='Aging Bucket', index=True)
    is_dead_stock = fields.Boolean(string='Dead Stock', index=True)
    dead_stock_score = fields.Float(string='Dead Stock Score')
    turnover_rate_30d = fields.Float(string='Turnover 30d')
    sold_qty_30d = fields.Float(string='Sold Qty 30d')
    suggested_reorder_qty = fields.Float(string='Suggested Reorder Qty')
    reorder_priority = fields.Selection([
        ('none', 'None'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Reorder Priority', index=True)
    reorder_reason = fields.Char(string='Reorder Reason')
    company_id = fields.Many2one(related='analysis_id.company_id', store=True, index=True)
