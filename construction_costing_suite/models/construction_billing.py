# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class ConstructionMilestone(models.Model):
    _name = 'construction.milestone'
    _description = 'Construction Milestone'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, planned_date'

    name = fields.Char(string='Milestone Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    code = fields.Char(string='Milestone Code')
    is_reached = fields.Boolean(string='Milestone Code')
    deadline = fields.Date(string='Milestone Code')

    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade')
    task_id = fields.Many2one('project.task', string='Related Task')

    planned_date = fields.Date(string='Planned Date', required=True)
    actual_date = fields.Date(string='Actual Date')

    amount = fields.Monetary(string='Milestone Amount', currency_field='currency_id', required=True, default=0.0)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    progress_percentage = fields.Float(string='Progress %', digits=(16, 2), default=0.0)
    is_completed = fields.Boolean(string='Completed', default=False)

    retainage_percentage = fields.Float(string='Retainage %', digits=(16, 2), default=0.0)
    retainage_amount = fields.Monetary(string='Retainage Amount', compute='_compute_retainage', store=True, currency_field='currency_id')
    net_amount = fields.Monetary(string='Net Amount', compute='_compute_retainage', store=True, currency_field='currency_id')

    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_date = fields.Date(string='Invoice Date')
    is_invoiced = fields.Boolean(string='Invoiced', default=False)

    state = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='planned', tracking=True)

    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    # IMPORTANT: Do NOT add any field named 'is_reached' here

    @api.depends('amount', 'retainage_percentage')
    def _compute_retainage(self):
        for milestone in self:
            milestone.retainage_amount = milestone.amount * (milestone.retainage_percentage / 100)
            milestone.net_amount = milestone.amount - milestone.retainage_amount

    @api.constrains('progress_percentage')
    def _check_progress(self):
        for milestone in self:
            if milestone.progress_percentage < 0 or milestone.progress_percentage > 100:
                raise ValidationError(_("Progress percentage must be between 0 and 100."))
            if milestone.progress_percentage >= 100 and not milestone.is_completed:
                milestone.is_completed = True

    def action_complete(self):
        for milestone in self:
            if milestone.state in ('completed', 'invoiced'):
                raise UserError(_("This milestone is already completed/invoiced."))
            milestone.state = 'completed'
            milestone.is_completed = True
            milestone.actual_date = fields.Date.today()
            milestone.progress_percentage = 100.0

    def action_generate_invoice(self):
        for milestone in self:
            if milestone.is_invoiced:
                raise UserError(_("This milestone has already been invoiced."))
            if milestone.state != 'completed':
                raise UserError(_("Milestone must be completed before invoicing."))

            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': milestone.project_id.partner_id.id,
                'company_id': milestone.company_id.id,
                'currency_id': milestone.currency_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [(0, 0, {
                    'name': _("Milestone: %s - %s") % (milestone.code or '', milestone.name),
                    'quantity': 1.0,
                    'price_unit': milestone.net_amount,
                    'tax_ids': [(6, 0, [])],
                    'project_id': milestone.project_id.id,
                })]
            }

            invoice = self.env['account.move'].create(invoice_vals)
            invoice.action_post()

            milestone.invoice_id = invoice.id
            milestone.invoice_date = fields.Date.today()
            milestone.is_invoiced = True
            milestone.state = 'invoiced'

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoice.id,
                'view_mode': 'form',
            }

    def action_view_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.invoice_id.id,
                'view_mode': 'form',
            }


class ConstructionProgressBilling(models.Model):
    _name = 'construction.progress.billing'
    _description = 'Construction Progress Billing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'billing_date desc, id desc'

    name = fields.Char(string='Billing Number', required=True, copy=False, default='New')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    project_id = fields.Many2one('project.project', string='Project', required=True)
    billing_date = fields.Date(string='Billing Date', required=True, default=fields.Date.today)

    billing_method = fields.Selection([
        ('milestone', 'Milestone Based'),
        ('percentage', 'Percentage Completion'),
        ('time_materials', 'Time & Materials'),
        ('fixed_price', 'Fixed Price')
    ], string='Billing Method', required=True, default='milestone')

    billed_amount = fields.Monetary(string='Billed Amount', currency_field='currency_id')
    retainage_percentage = fields.Float(string='Retainage %', default=10.0)
    retainage_amount = fields.Monetary(string='Retainage Amount', compute='_compute_retainage_amounts', store=True, currency_field='currency_id')
    net_amount = fields.Monetary(string='Net Billed Amount', compute='_compute_retainage_amounts', store=True, currency_field='currency_id')

    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_ids = fields.One2many('account.move', 'construction_progress_billing_id', string='Invoices')

    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('invoiced', 'Invoiced'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    @api.depends('billed_amount', 'retainage_percentage')
    def _compute_retainage_amounts(self):
        for billing in self:
            billing.retainage_amount = billing.billed_amount * (billing.retainage_percentage / 100)
            billing.net_amount = billing.billed_amount - billing.retainage_amount

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            seq = self.env['ir.sequence'].next_by_code('construction.progress.billing') or 'New'
            vals['name'] = seq
        return super(ConstructionProgressBilling, self).create(vals)

    def action_approve(self):
        for billing in self:
            if billing.state != 'draft':
                raise UserError(_("Only draft billings can be approved."))
            billing.state = 'approved'

    def action_generate_invoice(self):
        for billing in self:
            if billing.state not in ('draft', 'approved'):
                raise UserError(_("Cannot invoice a %s billing.") % billing.state)

            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': billing.project_id.partner_id.id,
                'company_id': billing.company_id.id,
                'currency_id': billing.currency_id.id,
                'invoice_date': billing.billing_date,
                'construction_progress_billing_id': billing.id,
                'invoice_line_ids': [(0, 0, {
                    'name': _("Progress Billing: %s") % billing.name,
                    'quantity': 1.0,
                    'price_unit': billing.net_amount,
                    'tax_ids': [(6, 0, [])],
                    'project_id': billing.project_id.id,
                })]
            }

            invoice = self.env['account.move'].create(invoice_vals)
            invoice.action_post()

            billing.invoice_id = invoice.id
            billing.state = 'invoiced'

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
            'domain': [('construction_progress_billing_id', '=', self.id)],
        }


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    construction_progress_billing_id = fields.Many2one('construction.progress.billing', string='Construction Billing')
    construction_milestone_id = fields.Many2one('construction.milestone', string='Construction Milestone')