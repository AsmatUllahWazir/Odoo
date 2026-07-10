# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ConstructionBOQ(models.Model):
    _name = 'construction.boq'
    _description = 'Construction Bill of Quantities'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='BOQ Reference', required=True, copy=False, default='New')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id,
                                  required=True)

    date = fields.Date(string='Date', default=fields.Date.today)
    validity_date = fields.Date(string='Validity Date')

    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade')

    line_ids = fields.One2many('construction.boq.line', 'boq_id', string='BOQ Lines', copy=True)

    total = fields.Monetary(string='Total Amount', compute='_compute_totals', store=True, currency_field='currency_id')
    total_quantity = fields.Float(string='Total Quantity', compute='_compute_totals', store=True, digits=(16, 2))

    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    approved_by = fields.Many2one('res.users', string='Approved By', tracking=True)
    approval_date = fields.Date(string='Approval Date')
    rejected_reason = fields.Text(string='Rejection Reason')

    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    version = fields.Integer(string='Version', default=1)
    previous_version_id = fields.Many2one('construction.boq', string='Previous Version')

    @api.depends('line_ids', 'line_ids.subtotal')
    def _compute_totals(self):
        for boq in self:
            boq.total = sum(boq.line_ids.mapped('subtotal'))
            boq.total_quantity = sum(boq.line_ids.mapped('quantity'))

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            seq = self.env['ir.sequence'].next_by_code('construction.boq') or 'New'
            vals['name'] = seq
        return super(ConstructionBOQ, self).create(vals)

    def action_approve(self):
        for boq in self:
            if boq.state in ('approved', 'cancelled'):
                raise UserError(_("Cannot approve a %s BOQ.") % boq.state)
            if not boq.line_ids:
                raise UserError(_("Cannot approve an empty BOQ."))
            boq.state = 'approved'
            boq.approved_by = self.env.user
            boq.approval_date = fields.Date.today()
            boq._create_job_cost_lines()
            boq._create_material_requisitions()

    def _create_job_cost_lines(self):
        JobCostLine = self.env['construction.job.cost.line']
        for boq in self:
            for line in boq.line_ids:
                if line.product_id:
                    existing = JobCostLine.search([
                        ('project_id', '=', boq.project_id.id),
                        ('product_id', '=', line.product_id.id),
                        ('boq_line_id', '=', line.id)
                    ])
                    if not existing:
                        cost_line_vals = {
                            'project_id': boq.project_id.id,
                            'boq_line_id': line.id,
                            'product_id': line.product_id.id,
                            'category': line.category,
                            'name': line.description or line.product_id.name,
                            'budgeted_quantity': line.quantity,
                            'budgeted_unit_price': line.unit_price,
                            'budgeted_amount': line.subtotal,
                            'uom_id': line.uom_id.id,
                        }
                        JobCostLine.create(cost_line_vals)

    def _create_material_requisitions(self):
        Requisition = self.env['construction.material.requisition']
        RequisitionLine = self.env['construction.material.requisition.line']
        for boq in self:
            lines_by_product = {}
            for line in boq.line_ids:
                if line.create_requisition and line.product_id:
                    key = (line.product_id.id, line.category)
                    if key not in lines_by_product:
                        lines_by_product[key] = []
                    lines_by_product[key].append(line)
            for (product_id, category), lines in lines_by_product.items():
                total_quantity = sum(l.quantity for l in lines)
                requisition_vals = {
                    'project_id': boq.project_id.id,
                    'name': _("BOQ Requisition: %s") % boq.name,
                    'requisition_date': fields.Date.today(),
                    'notes': _("Auto-generated from BOQ %s") % boq.name,
                    'company_id': boq.company_id.id,
                }
                requisition = Requisition.create(requisition_vals)
                for line in lines:
                    line_vals = {
                        'requisition_id': requisition.id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'uom_id': line.uom_id.id,
                        'estimated_unit_price': line.unit_price,
                        'notes': line.description or line.product_id.name,
                        'boq_line_id': line.id,
                    }
                    RequisitionLine.create(line_vals)
                requisition.action_submit()

    def action_review(self):
        for boq in self:
            if boq.state != 'draft':
                raise UserError(_("Only draft BOQs can be sent for review."))
            boq.state = 'under_review'

    def action_reject(self):
        for boq in self:
            boq.state = 'rejected'

    def action_cancel(self):
        for boq in self:
            boq.state = 'cancelled'

    def action_set_draft(self):
        for boq in self:
            boq.state = 'draft'


class ConstructionBOQLine(models.Model):
    _name = 'construction.boq.line'
    _description = 'Construction BOQ Line'
    _order = 'sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    boq_id = fields.Many2one('construction.boq', string='BOQ', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    product_id = fields.Many2one('product.product', string='Product/Service', required=True)
    category = fields.Selection([
        ('materials', 'Materials'),
        ('labor', 'Labor'),
        ('subcontractor', 'Subcontractors'),
        ('equipment', 'Equipment'),
        ('overhead', 'Overheads'),
        ('other', 'Other')
    ], string='Category', required=True, default='materials')

    quantity = fields.Float(string='Quantity', required=True, default=1.0, digits=(16, 2))
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    unit_price = fields.Monetary(string='Unit Price', required=True, currency_field='currency_id', default=0.0)
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='boq_id.currency_id', string='Currency', store=True)

    description = fields.Text(string='Description')
    variance_allowed = fields.Float(string='Variance Allowed %', default=10.0)
    assigned_task_id = fields.Many2one('project.task', string='Assigned Task')
    create_requisition = fields.Boolean(string='Create Requisition', default=False)

    actual_cost = fields.Monetary(string='Actual Cost', currency_field='currency_id', default=0.0)
    cost_variance = fields.Monetary(string='Cost Variance', compute='_compute_actual_cost', store=True,
                                    currency_field='currency_id')

    project_id = fields.Many2one(related='boq_id.project_id', string='Project', store=True)
    company_id = fields.Many2one(related='boq_id.company_id', string='Company', store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.depends('actual_cost')
    def _compute_actual_cost(self):
        for line in self:
            cost_line = self.env['construction.job.cost.line'].search([('boq_line_id', '=', line.id)], limit=1)
            if cost_line:
                line.actual_cost = cost_line.actual_cost
                line.cost_variance = line.subtotal - cost_line.actual_cost
            else:
                line.actual_cost = 0.0
                line.cost_variance = line.subtotal

    @api.constrains('quantity', 'unit_price')
    def _check_positive_values(self):
        for line in self:
            if line.quantity < 0:
                raise ValidationError(_("Quantity cannot be negative."))
            if line.unit_price < 0:
                raise ValidationError(_("Unit price cannot be negative."))

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            self.description = self.product_id.description_sale or self.product_id.name
            