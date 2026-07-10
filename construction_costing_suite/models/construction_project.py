# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_construction_project = fields.Boolean(string='Construction Project', default=False)
    project_type = fields.Selection([
        ('new_construction', 'New Construction'),
        ('renovation', 'Renovation/Remodel'),
        ('addition', 'Addition/Extension'),
        ('demolition', 'Demolition'),
        ('infrastructure', 'Infrastructure'),
        ('commercial', 'Commercial'),
        ('residential', 'Residential'),
        ('industrial', 'Industrial'),
        ('maintenance', 'Maintenance/Repair'),
        ('other', 'Other')
    ], string='Project Type', default='new_construction')

    construction_status = fields.Selection([
        ('draft', 'Draft'),
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Construction Status', default='draft', tracking=True)

    site_address = fields.Text(string='Site Address')
    site_contact = fields.Char(string='Site Contact')
    site_phone = fields.Char(string='Site Phone')

    total_contract_value = fields.Monetary(string='Total Contract Value', currency_field='currency_id', tracking=True)
    total_budget = fields.Monetary(string='Total Budget', currency_field='currency_id', compute='_compute_totals',
                                   store=True)
    total_actual_cost = fields.Monetary(string='Total Actual Cost', currency_field='currency_id',
                                        compute='_compute_totals', store=True)
    total_committed = fields.Monetary(string='Total Committed', currency_field='currency_id', compute='_compute_totals',
                                      store=True)
    # total_billed = fields.Monetary(string='Total Billed', currency_field='currency_id', compute='_compute_billing', store=True)
    total_billed = fields.Monetary(string='Total Billed', currency_field='currency_id', store=True)

    physical_completion = fields.Float(string='Physical Completion %', compute='_compute_completion', store=True,
                                       digits=(16, 2))
    financial_completion = fields.Float(string='Financial Completion %', compute='_compute_completion', store=True,
                                        digits=(16, 2))
    cost_variance = fields.Monetary(string='Cost Variance', compute='_compute_completion', store=True,
                                    currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    boq_ids = fields.One2many('construction.boq', 'project_id', string='BOQs')
    requisition_ids = fields.One2many('construction.material.requisition', 'project_id', string='Requisitions')
    milestone_ids = fields.One2many('construction.milestone', 'project_id', string='Milestones')
    job_cost_line_ids = fields.One2many('construction.job.cost.line', 'project_id', string='Job Costs')
    checklist_ids = fields.One2many('construction.checklist', 'project_id', string='Checklists')
    subcontractor_task_ids = fields.One2many('construction.subcontractor.task', 'project_id',
                                             string='Subcontractor Tasks')

    boq_count = fields.Integer(compute='_compute_counts', string='BOQs')
    requisition_count = fields.Integer(compute='_compute_counts', string='Requisitions')
    milestone_count = fields.Integer(compute='_compute_counts', string='Milestones')
    cost_line_count = fields.Integer(compute='_compute_counts', string='Cost Lines')

    @api.depends('boq_ids', 'boq_ids.total', 'job_cost_line_ids', 'job_cost_line_ids.actual_cost',
                 'job_cost_line_ids.committed_cost')
    def _compute_totals(self):
        for project in self:
            project.total_budget = sum(project.boq_ids.mapped('total'))
            project.total_actual_cost = sum(project.job_cost_line_ids.mapped('actual_cost'))
            project.total_committed = sum(project.job_cost_line_ids.mapped('committed_cost'))

    # @api.depends('account_move_ids', 'account_move_ids.amount_total')
    # def _compute_billing(self):
    #     for project in self:
    #         invoices = project.account_move_ids.filtered(
    #             lambda m: m.move_type in ('out_invoice', 'out_refund') and m.state == 'posted')
    #         project.total_billed = sum(invoices.mapped('amount_total')) or 0.0

    @api.depends('task_ids', 'task_ids.stage_id', 'total_actual_cost', 'total_budget')
    def _compute_completion(self):
        for project in self:
            if project.task_ids:
                done_tasks = project.task_ids.filtered(lambda t: t.stage_id and t.stage_id.fold)
                project.physical_completion = (len(done_tasks) / len(
                    project.task_ids)) * 100 if project.task_ids else 0.0
            else:
                project.physical_completion = 0.0

            if project.total_budget > 0:
                project.financial_completion = (project.total_actual_cost / project.total_budget) * 100
            else:
                project.financial_completion = 0.0

            if project.total_actual_cost > 0:
                earned_value = (project.physical_completion / 100) * project.total_budget
                project.cost_variance = earned_value - project.total_actual_cost
            else:
                project.cost_variance = 0.0

    def _compute_counts(self):
        for project in self:
            project.boq_count = len(project.boq_ids)
            project.requisition_count = len(project.requisition_ids)
            project.milestone_count = len(project.milestone_ids)
            project.cost_line_count = len(project.job_cost_line_ids)

    def action_show_dashboard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.dashboard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_project_id': self.id},
        }

    def action_open_boqs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.boq',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_costs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.job.cost.line',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.material.requisition',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_open_milestones(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.milestone',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    @api.model
    def create(self, vals):
        if vals.get('project_type'):
            vals['is_construction_project'] = True
        return super(ProjectProject, self).create(vals)


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    is_closed = fields.Boolean(string='Closed', related='fold', store=False)
    is_close = fields.Boolean(string='Closed', related='fold', store=False)

# IMPORTANT: Remove the problematic field override completely
# Do NOT add any field called 'is_reached' or any compute that depends on it