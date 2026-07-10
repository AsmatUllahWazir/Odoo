# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ConstructionJobCostLine(models.Model):
    _name = 'construction.job.cost.line'
    _description = 'Construction Job Cost Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'category, product_id'

    name = fields.Char(string='Description', required=True, default=lambda self: _('New Cost Line'))
    category = fields.Selection([
        ('materials', 'Materials'),
        ('labor', 'Labor'),
        ('subcontractor', 'Subcontractors'),
        ('equipment', 'Equipment'),
        ('overhead', 'Overheads'),
        ('other', 'Other')
    ], string='Category', required=True, default='materials')

    product_id = fields.Many2one('product.product', string='Product/Service')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')

    budgeted_quantity = fields.Float(string='Budgeted Quantity', digits=(16, 2), default=1.0)
    budgeted_unit_price = fields.Monetary(string='Budgeted Unit Price', currency_field='currency_id', default=0.0)
    budgeted_amount = fields.Monetary(string='Budgeted Amount', compute='_compute_budgeted_amount', store=True, currency_field='currency_id')

    actual_quantity = fields.Float(string='Actual Quantity', compute='_compute_actuals', store=True, digits=(16, 2))
    actual_unit_price = fields.Monetary(string='Actual Unit Price', compute='_compute_actuals', store=True, currency_field='currency_id')
    actual_cost = fields.Monetary(string='Actual Cost', compute='_compute_actuals', store=True, currency_field='currency_id')

    committed_quantity = fields.Float(string='Committed Quantity', digits=(16, 2), default=0.0)
    committed_cost = fields.Monetary(string='Committed Cost', currency_field='currency_id', default=0.0)

    cost_variance = fields.Monetary(string='Cost Variance', compute='_compute_variances', store=True, currency_field='currency_id')
    quantity_variance = fields.Float(string='Quantity Variance', compute='_compute_variances', store=True, digits=(16, 2))

    completion_percentage = fields.Float(string='Completion %', compute='_compute_completion', store=True, digits=(16, 2))

    boq_line_id = fields.Many2one('construction.boq.line', string='BOQ Line Reference')

    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade')
    task_id = fields.Many2one('project.task', string='Task')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.depends('budgeted_quantity', 'budgeted_unit_price')
    def _compute_budgeted_amount(self):
        for line in self:
            line.budgeted_amount = line.budgeted_quantity * line.budgeted_unit_price

    @api.depends('product_id', 'task_id', 'project_id')
    def _compute_actuals(self):
        for line in self:
            actual_qty = 0.0
            actual_cost = 0.0

            if line.product_id:
                purchase_lines = self.env['purchase.order.line'].search([
                    ('product_id', '=', line.product_id.id),
                    ('order_id.project_id', '=', line.project_id.id),
                    ('state', 'in', ['purchase', 'done'])
                ])
                for po_line in purchase_lines:
                    actual_qty += po_line.qty_received
                    actual_cost += po_line.price_subtotal

                if line.category in ('labor', 'subcontractor'):
                    timesheets = self.env['account.analytic.line'].search([
                        ('product_id', '=', line.product_id.id),
                        ('project_id', '=', line.project_id.id),
                    ])
                    for ts in timesheets:
                        actual_qty += ts.unit_amount
                        actual_cost += ts.amount

            line.actual_quantity = actual_qty
            if actual_qty > 0:
                line.actual_unit_price = actual_cost / actual_qty
            else:
                line.actual_unit_price = 0.0
            line.actual_cost = actual_cost

    @api.depends('budgeted_amount', 'actual_cost')
    def _compute_variances(self):
        for line in self:
            line.cost_variance = line.budgeted_amount - line.actual_cost
            line.quantity_variance = line.budgeted_quantity - line.actual_quantity

    @api.depends('actual_quantity', 'budgeted_quantity')
    def _compute_completion(self):
        for line in self:
            if line.budgeted_quantity > 0:
                line.completion_percentage = (line.actual_quantity / line.budgeted_quantity) * 100
            else:
                line.completion_percentage = 0.0

    @api.constrains('budgeted_amount')
    def _check_budget_amount(self):
        for line in self:
            if line.budgeted_amount < 0:
                raise ValidationError(_("Budgeted amount cannot be negative."))

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form',
            'domain': [
                ('project_id', '=', self.project_id.id),
                ('order_line.product_id', '=', self.product_id.id) if self.product_id else []
            ],
        }

    def action_view_timesheets(self):
        self.ensure_one()
        return {
            'name': _('Timesheets'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_mode': 'tree,form',
            'domain': [
                ('project_id', '=', self.project_id.id),
                ('product_id', '=', self.product_id.id) if self.product_id else [],
            ],
        }
