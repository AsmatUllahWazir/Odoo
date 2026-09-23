# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # ===== Aging & Movement =====
    last_move_date = fields.Datetime(
        string='Last Stock Move',
        compute='_compute_aging_fields',
        store=True,
        index=True,
        help='Most recent done stock move date for this product'
    )
    days_since_last_move = fields.Integer(
        string='Days Since Last Move',
        compute='_compute_aging_fields',
        store=True,
        index=True,
    )
    aging_bucket = fields.Selection([
        ('0_30', '0-30 Days'),
        ('31_60', '31-60 Days'),
        ('61_90', '61-90 Days'),
        ('90_plus', '90+ Days'),
        ('no_move', 'No Movement'),
    ], string='Aging Bucket', compute='_compute_aging_fields', store=True, index=True)

    is_dead_stock = fields.Boolean(
        string='Dead Stock',
        compute='_compute_aging_fields',
        store=True,
        index=True,
        help='Product has quantity on hand and has not moved for longer than the configured threshold'
    )
    dead_stock_score = fields.Float(
        string='Dead Stock Score',
        compute='_compute_aging_fields',
        store=True,
        help='Composite score: higher = more urgent to address (days × quantity factor × value factor)'
    )

    # ===== Value & Performance =====
    stock_value_aging = fields.Monetary(
        string='Stock Value',
        compute='_compute_stock_value_aging',
        store=True,
        currency_field='company_currency_id',
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        readonly=True,
    )
    turnover_rate_30d = fields.Float(
        string='Turnover Rate (30 days)',
        compute='_compute_turnover',
        store=True,
        digits=(16, 2),
        help='Quantity delivered to customers in last 30 days / current available qty'
    )
    sold_qty_30d = fields.Float(
        string='Sold Qty (30d)',
        compute='_compute_turnover',
        store=True,
    )

    # ===== Reorder Intelligence =====
    suggested_reorder_qty = fields.Float(
        string='Suggested Reorder Qty',
        compute='_compute_reorder_suggestion',
        store=True,
    )
    reorder_priority = fields.Selection([
        ('none', 'None'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Reorder Priority', compute='_compute_reorder_suggestion', store=True, index=True)
    reorder_reason = fields.Char(
        string='Reorder Reason',
        compute='_compute_reorder_suggestion',
        store=True,
    )

    # ===== Helpers =====
    @api.depends(
        'stock_move_ids.state',
        'stock_move_ids.date',
        'qty_available',
        'standard_price',
    )
    def _compute_aging_fields(self):
        ICP = self.env['ir.config_parameter'].sudo()
        dead_threshold = int(ICP.get_param('smart_inventory_analytics.dead_stock_days', 90))

        for product in self:
            # Get latest done move
            last_move = self.env['stock.move'].search([
                ('product_id', '=', product.id),
                ('state', '=', 'done'),
            ], order='date desc', limit=1)

            if last_move:
                last_date = last_move.date
                product.last_move_date = last_date
                days = (fields.Datetime.now() - last_date).days
                product.days_since_last_move = max(days, 0)

                if days <= 30:
                    product.aging_bucket = '0_30'
                elif days <= 60:
                    product.aging_bucket = '31_60'
                elif days <= 90:
                    product.aging_bucket = '61_90'
                else:
                    product.aging_bucket = '90_plus'

                product.is_dead_stock = bool(
                    product.qty_available > 0 and days >= dead_threshold
                )
            else:
                product.last_move_date = False
                product.days_since_last_move = 9999
                product.aging_bucket = 'no_move'
                product.is_dead_stock = product.qty_available > 0

            # Score calculation
            days_for_score = product.days_since_last_move or 0
            qty_factor = 1.0 + (product.qty_available / 20.0)
            value_factor = max(product.standard_price, 1.0) / 50.0
            product.dead_stock_score = round(days_for_score * qty_factor * value_factor, 2)

    @api.depends('qty_available', 'standard_price')
    def _compute_stock_value_aging(self):
        for product in self:
            product.stock_value_aging = product.qty_available * product.standard_price

    @api.depends('stock_move_ids.state', 'stock_move_ids.date', 'stock_move_ids.product_uom_qty', 'qty_available')
    def _compute_turnover(self):
        date_from = fields.Datetime.now() - timedelta(days=30)
        Move = self.env['stock.move']

        for product in self:
            outgoing = Move.search([
                ('product_id', '=', product.id),
                ('state', '=', 'done'),
                ('date', '>=', date_from),
                ('location_dest_id.usage', '=', 'customer'),
            ])
            sold = sum(outgoing.mapped('product_uom_qty'))
            product.sold_qty_30d = sold
            avg_stock = product.qty_available or 1.0
            product.turnover_rate_30d = round(sold / avg_stock, 2) if avg_stock else 0.0

    @api.depends(
        'qty_available',
        'reordering_min_qty',
        'reordering_max_qty',
        'turnover_rate_30d',
        'days_since_last_move',
        'is_dead_stock',
    )
    def _compute_reorder_suggestion(self):
        for product in self:
            available = product.qty_available
            min_qty = product.reordering_min_qty or 0.0
            max_qty = product.reordering_max_qty or 0.0
            turnover = product.turnover_rate_30d

            suggested = 0.0
            priority = 'none'
            reason = ''

            if available <= 0 and (min_qty > 0 or turnover > 0.5):
                suggested = max_qty or max(min_qty * 2, 10.0)
                priority = 'critical'
                reason = 'Out of stock'
            elif min_qty > 0 and available < min_qty:
                suggested = max(max_qty - available, min_qty - available, 0.0)
                if available < min_qty * 0.3:
                    priority = 'critical'
                    reason = 'Far below minimum'
                elif available < min_qty * 0.6:
                    priority = 'high'
                    reason = 'Below minimum'
                else:
                    priority = 'medium'
                    reason = 'Approaching minimum'
            elif turnover >= 2.0 and available < (min_qty or 15):
                suggested = max((min_qty or 15) - available, 5.0)
                priority = 'high'
                reason = 'High velocity + low stock'
            elif turnover >= 1.0 and available < (min_qty or 10):
                suggested = max((min_qty or 10) - available, 0.0)
                priority = 'medium'
                reason = 'Good velocity'
            elif product.is_dead_stock:
                suggested = 0.0
                priority = 'none'
                reason = 'Dead stock – review / promote / liquidate'
            else:
                suggested = 0.0
                priority = 'low' if available > 0 else 'none'
                reason = ''

            product.suggested_reorder_qty = round(suggested, 2)
            product.reorder_priority = priority
            product.reorder_reason = reason


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    aging_bucket = fields.Selection(
        related='product_variant_id.aging_bucket',
        string='Aging Bucket',
        store=False,
        readonly=True,
    )
    is_dead_stock = fields.Boolean(
        related='product_variant_id.is_dead_stock',
        string='Dead Stock',
        store=False,
        readonly=True,
    )
    days_since_last_move = fields.Integer(
        related='product_variant_id.days_since_last_move',
        string='Days Since Last Move',
        store=False,
        readonly=True,
    )
    dead_stock_score = fields.Float(
        related='product_variant_id.dead_stock_score',
        string='Dead Stock Score',
        store=False,
        readonly=True,
    )
    reorder_priority = fields.Selection(
        related='product_variant_id.reorder_priority',
        string='Reorder Priority',
        store=False,
        readonly=True,
    )
