# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class GenerateInvoiceWizard(models.TransientModel):
    _name = 'generate.invoice.wizard'
    _description = 'Generate Progress Invoice'

    project_id = fields.Many2one('project.project', string='Project', required=True)
    billing_method = fields.Selection([
        ('milestone', 'Milestone Based'),
        ('percentage', 'Percentage Completion'),
        ('fixed', 'Fixed Amount')
    ], string='Billing Method', required=True, default='milestone')

    milestone_ids = fields.Many2many('construction.milestone', string='Milestones',
        domain="[('project_id', '=', project_id), ('state', '=', 'completed'), ('is_invoiced', '=', False)]")

    completion_percentage = fields.Float(string='Completion Percentage', digits=(16, 2), default=0.0)
    amount = fields.Monetary(string='Invoice Amount', currency_field='currency_id')

    retainage_percentage = fields.Float(string='Retainage %', digits=(16, 2), default=10.0)

    invoice_date = fields.Date(string='Invoice Date', default=fields.Date.today)
    due_date = fields.Date(string='Due Date', default=lambda self: fields.Date.today() + timedelta(days=30))

    description = fields.Text(string='Description')

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.onchange('project_id')
    def _onchange_project(self):
        if self.project_id:
            return {
                'domain': {
                    'milestone_ids': [
                        ('project_id', '=', self.project_id.id),
                        ('state', '=', 'completed'),
                        ('is_invoiced', '=', False)
                    ]
                }
            }

    def action_generate_invoice(self):
        self.ensure_one()

        if not self.project_id:
            raise UserError(_("Please select a project."))

        invoice_lines = []
        amount_to_invoice = 0.0

        if self.billing_method == 'milestone':
            if not self.milestone_ids:
                raise UserError(_("Please select at least one milestone."))
            for milestone in self.milestone_ids:
                invoice_lines.append({
                    'name': _("Milestone: %s - %s") % (milestone.code or '', milestone.name),
                    'quantity': 1.0,
                    'price_unit': milestone.net_amount,
                })
                amount_to_invoice += milestone.net_amount

        elif self.billing_method == 'percentage':
            if self.completion_percentage <= 0:
                raise UserError(_("Please enter a valid completion percentage."))
            amount = self.project_id.total_contract_value * (self.completion_percentage / 100)
            already_billed = self.project_id.total_billed
            amount_to_invoice = max(0, amount - already_billed)
            if amount_to_invoice <= 0:
                raise UserError(_("No additional amount to invoice."))
            invoice_lines.append({
                'name': _("Progress Billing - %s%% Complete") % self.completion_percentage,
                'quantity': 1.0,
                'price_unit': amount_to_invoice,
            })

        elif self.billing_method == 'fixed':
            if self.amount <= 0:
                raise UserError(_("Please enter a valid invoice amount."))
            amount_to_invoice = self.amount
            invoice_lines.append({
                'name': _("Fixed Invoice"),
                'quantity': 1.0,
                'price_unit': amount_to_invoice,
            })

        retainage_amount = amount_to_invoice * (self.retainage_percentage / 100)
        net_amount = amount_to_invoice - retainage_amount

        if net_amount <= 0:
            raise UserError(_("Net amount is zero or negative after retainage."))

        if invoice_lines and self.retainage_percentage > 0:
            invoice_lines[0]['price_unit'] = net_amount
            if retainage_amount > 0:
                invoice_lines.append({
                    'name': _("Retainage (%s%%)") % self.retainage_percentage,
                    'quantity': 1.0,
                    'price_unit': -retainage_amount,
                })

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.project_id.partner_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_date': self.invoice_date,
            'invoice_date_due': self.due_date,
            'ref': _("Project: %s") % self.project_id.name,
            'project_id': self.project_id.id,
            'invoice_line_ids': [(0, 0, line) for line in invoice_lines],
            'invoice_origin': self.description or _("Progress invoice for %s") % self.project_id.name,
        }

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()

        if self.billing_method == 'milestone':
            for milestone in self.milestone_ids:
                milestone.is_invoiced = True
                milestone.state = 'invoiced'
                milestone.invoice_id = invoice.id
                milestone.invoice_date = self.invoice_date

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }
    