# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta

class ConstructionMaterialRequisition(models.Model):
    _name = 'construction.material.requisition'
    _description = 'Construction Material Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'requisition_date desc, id desc'

    name = fields.Char(string='Requisition Number', required=True, copy=False, default='New')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade')
    task_id = fields.Many2one('project.task', string='Task')

    requisition_date = fields.Date(string='Date', required=True, default=fields.Date.today)
    required_date = fields.Date(string='Required By', required=True, default=lambda self: fields.Date.today() + timedelta(days=7))

    source_location_id = fields.Many2one('stock.location', string='Source Location')
    destination_location_id = fields.Many2one('stock.location', string='Destination Location')

    line_ids = fields.One2many('construction.material.requisition.line', 'requisition_id', string='Requisition Lines')

    total_estimated = fields.Monetary(string='Total Estimated', compute='_compute_totals', store=True, currency_field='currency_id')
    total_actual = fields.Monetary(string='Total Actual', compute='_compute_totals', store=True, currency_field='currency_id')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('partially_delivered', 'Partially Delivered'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)

    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], string='Priority', default='normal')

    approved_by = fields.Many2one('res.users', string='Approved By', tracking=True)
    approval_date = fields.Date(string='Approval Date')
    rejected_reason = fields.Text(string='Rejection Reason')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    picking_ids = fields.Many2many('stock.picking', string='Related Pickings')

    @api.depends('line_ids', 'line_ids.estimated_subtotal', 'line_ids.actual_subtotal')
    def _compute_totals(self):
        for requisition in self:
            requisition.total_estimated = sum(requisition.line_ids.mapped('estimated_subtotal'))
            requisition.total_actual = sum(requisition.line_ids.mapped('actual_subtotal'))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            seq = self.env['ir.sequence'].next_by_code('construction.requisition') or 'New'
            vals['name'] = seq
        return super(ConstructionMaterialRequisition, self).create(vals)

    @api.constrains('required_date', 'requisition_date')
    def _check_dates(self):
        for requisition in self:
            if requisition.required_date < requisition.requisition_date:
                raise ValidationError(_("Required date cannot be before requisition date."))

    def action_submit(self):
        for requisition in self:
            if not requisition.line_ids:
                raise UserError(_("Cannot submit an empty requisition. Add at least one line."))
            if requisition.state == 'draft':
                requisition.state = 'submitted'

    def action_approve(self):
        for requisition in self:
            if requisition.state != 'submitted':
                raise UserError(_("Only submitted requisitions can be approved."))
            requisition.state = 'approved'
            requisition.approved_by = self.env.user
            requisition.approval_date = fields.Date.today()

    def action_reject(self):
        for requisition in self:
            if requisition.state != 'submitted':
                raise UserError(_("Only submitted requisitions can be rejected."))
            requisition.state = 'rejected'

    def action_cancel(self):
        for requisition in self:
            if requisition.state in ('delivered', 'partially_delivered'):
                raise UserError(_("Cannot cancel a delivered requisition."))
            requisition.state = 'cancelled'

    def action_set_draft(self):
        for requisition in self:
            if requisition.state != 'rejected':
                raise UserError(_("Only rejected requisitions can be set back to draft."))
            requisition.state = 'draft'

    def action_create_purchase_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'context': {
                'default_project_id': self.project_id.id,
            },
        }

    def action_view_pickings(self):
        self.ensure_one()
        return {
            'name': _('Pickings'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
        }


class ConstructionMaterialRequisitionLine(models.Model):
    _name = 'construction.material.requisition.line'
    _description = 'Construction Material Requisition Line'
    _order = 'requisition_id, sequence'

    requisition_id = fields.Many2one('construction.material.requisition', string='Requisition', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Char(string='Description')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)

    quantity = fields.Float(string='Quantity', required=True, default=1.0, digits=(16, 2))
    delivered_quantity = fields.Float(string='Delivered Quantity', compute='_compute_delivered', store=True, digits=(16, 2))
    remaining_quantity = fields.Float(string='Remaining', compute='_compute_remaining', store=True, digits=(16, 2))

    estimated_unit_price = fields.Monetary(string='Estimated Unit Price', currency_field='currency_id', default=0.0)
    estimated_subtotal = fields.Monetary(string='Estimated Subtotal', compute='_compute_estimated_subtotal', store=True, currency_field='currency_id')
    actual_unit_price = fields.Monetary(string='Actual Unit Price', currency_field='currency_id', default=0.0)
    actual_subtotal = fields.Monetary(string='Actual Subtotal', currency_field='currency_id', default=0.0)

    boq_line_id = fields.Many2one('construction.boq.line', string='BOQ Line Reference')
    picking_move_ids = fields.Many2many('stock.move', string='Related Stock Moves')

    company_id = fields.Many2one(related='requisition_id.company_id', string='Company', store=True)
    currency_id = fields.Many2one(related='requisition_id.currency_id', string='Currency', store=True)
    notes = fields.Text(string='Notes')

    @api.depends('quantity', 'estimated_unit_price')
    def _compute_estimated_subtotal(self):
        for line in self:
            line.estimated_subtotal = line.quantity * line.estimated_unit_price

    @api.depends('picking_move_ids', 'picking_move_ids.quantity', 'picking_move_ids.state')
    def _compute_delivered(self):
        for line in self:
            if line.picking_move_ids:
                delivered = sum(line.picking_move_ids.filtered(lambda m: m.state == 'done').mapped('quantity'))
                line.delivered_quantity = delivered
            else:
                line.delivered_quantity = 0.0

    @api.depends('quantity', 'delivered_quantity')
    def _compute_remaining(self):
        for line in self:
            line.remaining_quantity = line.quantity - line.delivered_quantity

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_("Quantity must be greater than zero."))

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.description = self.product_id.name
