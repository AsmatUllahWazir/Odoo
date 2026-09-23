# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    days_in_stock = fields.Integer(
        string='Days in Stock (approx)',
        compute='_compute_days_in_stock',
        help='Approximate days based on product last move date'
    )
    is_dead_stock_quant = fields.Boolean(
        string='Dead Stock',
        related='product_id.is_dead_stock',
        store=False,
        readonly=True,
    )
    aging_bucket_quant = fields.Selection(
        related='product_id.aging_bucket',
        string='Aging Bucket',
        store=False,
        readonly=True,
    )

    def _compute_days_in_stock(self):
        for quant in self:
            quant.days_in_stock = quant.product_id.days_since_last_move or 0
