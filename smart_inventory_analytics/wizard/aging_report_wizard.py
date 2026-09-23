# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AgingReportWizard(models.TransientModel):
    _name = 'aging.report.wizard'
    _description = 'Inventory Aging Report Wizard'

    date_to = fields.Date(string='As of Date', default=fields.Date.context_today, required=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    aging_bucket = fields.Selection([
        ('all', 'All Buckets'),
        ('0_30', '0-30 Days'),
        ('31_60', '31-60 Days'),
        ('61_90', '61-90 Days'),
        ('90_plus', '90+ Days'),
        ('no_move', 'No Movement'),
    ], string='Aging Bucket', default='all')
    only_dead_stock = fields.Boolean(string='Only Dead Stock')
    only_high_priority = fields.Boolean(string='Only High / Critical Reorder')
    product_ids = fields.Many2many('product.product', string='Limit to Products')
    include_zero_qty = fields.Boolean(
        string='Include Zero Quantity',
        help='Include products with zero on-hand (normally excluded)'
    )

    def _get_products(self):
        self.ensure_one()
        domain = [
            ('type', 'in', ['product', 'consu']),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id),
        ]
        if not self.include_zero_qty:
            domain.append(('qty_available', '>', 0))
        if self.only_dead_stock:
            domain.append(('is_dead_stock', '=', True))
        if self.only_high_priority:
            domain.append(('reorder_priority', 'in', ['high', 'critical']))
        if self.aging_bucket and self.aging_bucket != 'all':
            domain.append(('aging_bucket', '=', self.aging_bucket))
        if self.product_ids:
            domain.append(('id', 'in', self.product_ids.ids))

        return self.env['product.product'].with_company(self.company_id).search(
            domain, order='dead_stock_score desc'
        )

    def action_print_pdf(self):
        self.ensure_one()
        # Pass the wizard as doc so the template can use docs reliably
        return self.env.ref(
            'smart_inventory_analytics.action_report_inventory_aging'
        ).report_action(self)
