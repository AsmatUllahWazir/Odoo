# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CloseProjectWizard(models.TransientModel):
    _name = 'close.project.wizard'
    _description = 'Close Construction Project'

    project_id = fields.Many2one('project.project', string='Project', required=True)

    final_cost = fields.Monetary(string='Final Cost', currency_field='currency_id', compute='_compute_final_data', store=True)
    final_billed = fields.Monetary(string='Total Billed', currency_field='currency_id', compute='_compute_final_data', store=True)
    final_profit = fields.Monetary(string='Final Profit/Loss', currency_field='currency_id', compute='_compute_final_data', store=True)
    profit_margin = fields.Float(string='Profit Margin %', compute='_compute_final_data', store=True, digits=(16, 2))

    closure_reason = fields.Text(string='Closure Reason', required=True)
    closure_date = fields.Date(string='Closure Date', required=True, default=fields.Date.today)
    final_notes = fields.Text(string='Final Notes')

    final_status = fields.Selection([
        ('completed', 'Completed Successfully'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold - Suspended')
    ], string='Final Status', required=True, default='completed')

    release_retainage = fields.Boolean(string='Release Retainage', default=True)

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.depends('project_id')
    def _compute_final_data(self):
        for wizard in self:
            project = wizard.project_id
            if project:
                wizard.final_cost = project.total_actual_cost
                wizard.final_billed = project.total_billed
                wizard.final_profit = project.total_billed - project.total_actual_cost
                if project.total_billed > 0:
                    wizard.profit_margin = (wizard.final_profit / project.total_billed) * 100
                else:
                    wizard.profit_margin = 0.0

    def action_close_project(self):
        self.ensure_one()

        if not self.project_id:
            raise UserError(_("Please select a project."))

        project = self.project_id

        open_tasks = project.task_ids.filtered(lambda t: not t.stage_id.fold)
        if open_tasks and self.final_status == 'completed':
            raise UserError(_("Cannot close project as completed with open tasks."))

        closure_vals = {
            'construction_status': self.final_status,
        }

        notes = _("Closure Notes:\n%s\n\nFinal Cost: %s\nTotal Billed: %s\nFinal Profit: %s") % (
            self.closure_reason,
            self.final_cost,
            self.final_billed,
            self.final_profit
        )
        if self.final_notes:
            notes += f"\n\n{self.final_notes}"

        project.write(closure_vals)
        project.description = (project.description or '') + f"\n\n{notes}"
        project.active = False

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': project.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'form_view_initial_mode': 'view'},
        }

    def action_generate_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/construction_closing_report/' + str(self.id),
            'target': 'new',
        }

    def action_view_audit_trail(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.message',
            'view_mode': 'tree,form',
            'domain': [
                ('res_id', '=', self.project_id.id),
                ('model', '=', 'project.project')
            ],
            'target': 'new',
            'context': {'default_model': 'project.project', 'default_res_id': self.project_id.id},
        }
    