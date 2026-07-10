# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_construction_task = fields.Boolean(
        string='Construction Task',
        compute='_compute_is_construction_task',
        store=True
    )

    task_type = fields.Selection([
        ('preparation', 'Preparation'),
        ('foundation', 'Foundation'),
        ('structural', 'Structural'),
        ('enclosure', 'Enclosure'),
        ('interior', 'Interior'),
        ('finishing', 'Finishing'),
        ('exterior', 'Exterior'),
        ('landscaping', 'Landscaping'),
        ('inspection', 'Inspection'),
        ('handover', 'Handover'),
        ('other', 'Other')
    ], string='Task Type', default='other')

    location = fields.Char(string='Location/Area')
    team_lead = fields.Many2one('res.users', string='Team Lead')
    crew_members = fields.Many2many('res.users', string='Crew Members')

    estimated_cost = fields.Monetary(string='Estimated Cost', currency_field='currency_id', tracking=True, default=0.0)
    actual_cost = fields.Monetary(string='Actual Cost', currency_field='currency_id', default=0.0)
    cost_variance = fields.Monetary(string='Cost Variance', compute='_compute_actual_cost', store=True,
                                    currency_field='currency_id')

    physical_progress = fields.Float(string='Physical Progress %', compute='_compute_progress', store=True,
                                     digits=(16, 2))
    financial_progress = fields.Float(string='Financial Progress %', compute='_compute_progress', store=True,
                                      digits=(16, 2))

    estimated_start_date = fields.Date(string='Estimated Start Date')
    estimated_end_date = fields.Date(string='Estimated End Date')
    actual_start_date = fields.Date(string='Actual Start Date')
    actual_end_date = fields.Date(string='Actual End Date')

    quality_score = fields.Selection([
        ('1', 'Poor'),
        ('2', 'Below Average'),
        ('3', 'Average'),
        ('4', 'Good'),
        ('5', 'Excellent')
    ], string='Quality Score')
    quality_notes = fields.Text(string='Quality Notes')
    inspection_date = fields.Date(string='Inspection Date')
    inspection_passed = fields.Boolean(string='Inspection Passed')

    boq_line_ids = fields.Many2many('construction.boq.line', string='BOQ Lines')
    boq_count = fields.Integer(compute='_compute_boq_count', string='BOQ Count')

    requisition_ids = fields.One2many('construction.material.requisition', 'task_id', string='Material Requisitions')
    requisition_count = fields.Integer(compute='_compute_requisition_count', string='Requisition Count')

    job_cost_line_ids = fields.One2many('construction.job.cost.line', 'task_id', string='Job Cost Lines')

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    dependency_ids = fields.Many2many(
        'project.task',
        'task_dependency_rel',
        'task_id',
        'dependency_id',
        string='Dependencies'
    )
    dependent_ids = fields.Many2many(
        'project.task',
        'task_dependency_rel',
        'dependency_id',
        'task_id',
        string='Dependent Tasks'
    )

    subcontractor_task_ids = fields.One2many('construction.subcontractor.task', 'main_task_id',
                                             string='Subcontractor Tasks')

    @api.depends('project_id', 'project_id.is_construction_project')
    def _compute_is_construction_task(self):
        for task in self:
            task.is_construction_task = task.project_id.is_construction_project if task.project_id else False

    def _compute_boq_count(self):
        for task in self:
            task.boq_count = len(task.boq_line_ids)

    def _compute_requisition_count(self):
        for task in self:
            task.requisition_count = len(task.requisition_ids)

    @api.depends('stage_id', 'boq_line_ids', 'estimated_cost', 'job_cost_line_ids', 'job_cost_line_ids.actual_cost')
    def _compute_progress(self):
        for task in self:
            if task.stage_id.is_closed:
                task.physical_progress = 100.0
            else:
                task.physical_progress = 0.0

            if task.estimated_cost > 0:
                task.financial_progress = (task.actual_cost / task.estimated_cost) * 100
            else:
                task.financial_progress = 0.0

    @api.depends('job_cost_line_ids', 'job_cost_line_ids.actual_cost', 'estimated_cost')
    def _compute_actual_cost(self):
        for task in self:
            total_actual = sum(task.job_cost_line_ids.mapped('actual_cost'))
            task.actual_cost = total_actual
            task.cost_variance = task.estimated_cost - total_actual

    @api.constrains('estimated_start_date', 'estimated_end_date')
    def _check_dates(self):
        for task in self:
            if task.estimated_start_date and task.estimated_end_date:
                if task.estimated_end_date < task.estimated_start_date:
                    raise ValidationError(_("Estimated end date cannot be before estimated start date."))

    def action_start_task(self):
        for task in self:
            if task.stage_id.is_closed:
                raise UserError(_("Task is already completed."))
            if not task.actual_start_date:
                task.actual_start_date = fields.Date.today()

    def action_complete_task(self):
        for task in self:
            if task.stage_id.is_closed:
                raise UserError(_("Task is already completed."))
            incomplete_deps = task.dependency_ids.filtered(lambda d: not d.stage_id.is_closed)
            if incomplete_deps:
                raise UserError(_("Cannot complete task. Dependencies are not completed."))
            task.actual_end_date = fields.Date.today()
            task.physical_progress = 100.0
            if task.stage_id:
                stage = self.env['project.task.type'].search([('is_closed', '=', True)], limit=1)
                if stage:
                    task.stage_id = stage

    def action_view_boq_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.boq.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.boq_line_ids.ids)],
        }

    def action_view_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.material.requisition',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
        }

    def action_create_material_requisition(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.material.requisition',
            'view_mode': 'form',
            'context': {
                'default_project_id': self.project_id.id,
                'default_task_id': self.id,
                'default_name': _("Task Requisition: %s") % self.name,
                'default_required_date': self.date_deadline or fields.Date.today(),
            },
            'target': 'new',
        }

    def action_create_subtask(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'form',
            'context': {
                'default_project_id': self.project_id.id,
                'default_parent_id': self.id,
                'default_is_construction_task': self.is_construction_task,
            },
            'target': 'new',
        }
