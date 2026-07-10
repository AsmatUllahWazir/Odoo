# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_subcontractor = fields.Boolean(string='Is Subcontractor', default=False)
    subcontractor_rating = fields.Selection([
        ('1', '★ Poor'),
        ('2', '★★ Fair'),
        ('3', '★★★ Good'),
        ('4', '★★★★ Very Good'),
        ('5', '★★★★★ Excellent')
    ], string='Subcontractor Rating')

    insurance_expiry = fields.Date(string='Insurance Expiry Date')
    license_number = fields.Char(string='License Number')
    license_expiry = fields.Date(string='License Expiry Date')
    trade_classification = fields.Selection([
        ('general', 'General Contractor'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('hvac', 'HVAC'),
        ('carpentry', 'Carpentry'),
        ('painting', 'Painting'),
        ('roofing', 'Roofing'),
        ('concrete', 'Concrete'),
        ('landscaping', 'Landscaping'),
        ('other', 'Other')
    ], string='Trade Classification')

    bond_limit = fields.Monetary(string='Bond Limit', currency_field='currency_id')
    worker_compensation_rate = fields.Float(string='Worker\'s Comp Rate %', digits=(16, 2), default=0.0)
    subcontractor_task_count = fields.Integer(compute='_compute_subcontractor_task_count', string='Subcontractor Tasks')

    def _compute_subcontractor_task_count(self):
        for partner in self:
            partner.subcontractor_task_count = self.env['construction.subcontractor.task'].search_count([
                ('subcontractor_id', '=', partner.id)
            ])

    def action_view_subcontractor_tasks(self):
        self.ensure_one()
        return {
            'name': _('Subcontractor Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.subcontractor.task',
            'view_mode': 'tree,form',
            'domain': [('subcontractor_id', '=', self.id)],
        }

    @api.constrains('insurance_expiry', 'license_expiry')
    def _check_expiry_dates(self):
        for partner in self:
            if partner.insurance_expiry and partner.insurance_expiry < fields.Date.today():
                raise ValidationError(_("Insurance has expired. Please update."))
            if partner.license_expiry and partner.license_expiry < fields.Date.today():
                raise ValidationError(_("License has expired. Please update."))


class ConstructionSubcontractorTask(models.Model):
    _name = 'construction.subcontractor.task'
    _description = 'Subcontractor Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'deadline desc, id desc'

    name = fields.Char(string='Task Name', required=True, tracking=True)
    code = fields.Char(string='Task Code')

    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade')
    main_task_id = fields.Many2one('project.task', string='Main Task')

    subcontractor_id = fields.Many2one('res.partner', string='Subcontractor', required=True, domain=[('is_subcontractor', '=', True)])
    subcontractor_contact = fields.Char(string='Subcontractor Contact')
    subcontractor_phone = fields.Char(string='Phone', related='subcontractor_id.phone')
    subcontractor_email = fields.Char(string='Email', related='subcontractor_id.email')

    assignment_date = fields.Date(string='Assignment Date', default=fields.Date.today)
    deadline = fields.Date(string='Deadline', required=True)
    completion_date = fields.Date(string='Completion Date')

    description = fields.Text(string='Description')
    scope_of_work = fields.Text(string='Scope of Work')
    contract_value = fields.Monetary(string='Contract Value', currency_field='currency_id', required=True, default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    progress_percentage = fields.Float(string='Progress %', digits=(16, 2), default=0.0)
    status = fields.Selection([
        ('pending', 'Pending Assignment'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('under_review', 'Under Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', tracking=True)

    invoiced_amount = fields.Monetary(string='Invoiced Amount', compute='_compute_invoiced_amount', store=True, currency_field='currency_id')
    remaining_amount = fields.Monetary(string='Remaining Amount', compute='_compute_invoiced_amount', store=True, currency_field='currency_id')
    invoice_ids = fields.Many2many('account.move', string='Invoices')

    quality_rating = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Below Average'),
        ('3', 'Average'),
        ('4', 'Good'),
        ('5', 'Excellent')
    ], string='Quality Rating')
    quality_notes = fields.Text(string='Quality Notes')

    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    @api.depends('invoice_ids', 'invoice_ids.amount_total')
    def _compute_invoiced_amount(self):
        for task in self:
            total_invoiced = sum(task.invoice_ids.filtered(lambda i: i.state == 'posted').mapped('amount_total'))
            task.invoiced_amount = total_invoiced
            task.remaining_amount = task.contract_value - total_invoiced

    @api.constrains('deadline')
    def _check_deadline(self):
        for task in self:
            if task.deadline < fields.Date.today() and task.status not in ('completed', 'cancelled'):
                pass

    def action_assign(self):
        for task in self:
            if task.status != 'pending':
                raise UserError(_("Task must be pending to assign."))
            task.status = 'assigned'
            task.assignment_date = fields.Date.today()

    def action_start_work(self):
        for task in self:
            if task.status not in ('assigned', 'pending'):
                raise UserError(_("Task must be assigned to start work."))
            task.status = 'in_progress'

    def action_complete(self):
        for task in self:
            if task.status == 'completed':
                raise UserError(_("Task is already completed."))
            task.status = 'completed'
            task.completion_date = fields.Date.today()
            task.progress_percentage = 100.0

    def action_generate_invoice(self):
        self.ensure_one()
        if self.remaining_amount <= 0:
            raise UserError(_("No remaining amount to invoice."))
        if self.status != 'completed':
            raise UserError(_("Task must be completed before invoicing."))

        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.subcontractor_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'name': _("Subcontractor Work: %s - %s") % (self.code or '', self.name),
                'quantity': 1.0,
                'price_unit': self.remaining_amount,
                'tax_ids': [(6, 0, [])],
                'project_id': self.project_id.id,
            })]
        }

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()

        self.invoice_ids = [(4, invoice.id)]

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.invoice_ids.ids)],
        }
