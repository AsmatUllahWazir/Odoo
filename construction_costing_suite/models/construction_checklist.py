# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class ConstructionChecklistTemplate(models.Model):
    _name = 'construction.checklist.template'
    _description = 'Construction Checklist Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True)
    code = fields.Char(string='Template Code')
    project_type = fields.Selection([
        ('new_construction', 'New Construction'),
        ('renovation', 'Renovation'),
        ('addition', 'Addition'),
        ('demolition', 'Demolition'),
        ('infrastructure', 'Infrastructure'),
        ('commercial', 'Commercial'),
        ('residential', 'Residential')
    ], string='Project Type')

    template_lines = fields.One2many('construction.checklist.template.line', 'template_id', string='Checklist Items')

    category = fields.Selection([
        ('safety', 'Safety'),
        ('quality', 'Quality'),
        ('compliance', 'Compliance'),
        ('environmental', 'Environmental'),
        ('pre_construction', 'Pre-Construction'),
        ('post_construction', 'Post-Construction')
    ], string='Category', required=True, default='safety')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    def action_apply_to_project(self, project_id):
        if not project_id:
            raise UserError(_("Please select a project."))

        checklist_vals = {
            'name': _("%s Checklist") % self.name,
            'project_id': project_id.id,
            'template_id': self.id,
            'category': self.category,
            'company_id': self.company_id.id or self.env.company.id,
        }
        checklist = self.env['construction.checklist'].create(checklist_vals)

        for line in self.template_lines:
            line_vals = {
                'checklist_id': checklist.id,
                'description': line.description,
                'sequence': line.sequence,
                'required_before_start': line.required_before_start,
            }
            self.env['construction.checklist.line'].create(line_vals)

        return checklist

    def action_view_applied_checklists(self):
        self.ensure_one()
        return {
            'name': _('Applied Checklists'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.checklist',
            'view_mode': 'tree,form',
            'domain': [('template_id', '=', self.id)],
        }


class ConstructionChecklistTemplateLine(models.Model):
    _name = 'construction.checklist.template.line'
    _description = 'Checklist Template Item'
    _order = 'template_id, sequence'

    template_id = fields.Many2one('construction.checklist.template', string='Template', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description', required=True)
    required_before_start = fields.Boolean(string='Required Before Start', default=False)
    notes = fields.Text(string='Notes')


class ConstructionChecklist(models.Model):
    _name = 'construction.checklist'
    _description = 'Construction Checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Checklist Name', required=True)
    project_id = fields.Many2one('project.project', string='Project', required=True, ondelete='cascade')
    template_id = fields.Many2one('construction.checklist.template', string='Template')

    lines = fields.One2many('construction.checklist.line', 'checklist_id', string='Checklist Items', copy=True)

    category = fields.Selection([
        ('safety', 'Safety'),
        ('quality', 'Quality'),
        ('compliance', 'Compliance'),
        ('environmental', 'Environmental'),
        ('pre_construction', 'Pre-Construction'),
        ('post_construction', 'Post-Construction')
    ], string='Category', required=True, default='safety')

    date = fields.Date(string='Date', default=fields.Date.today)
    conducted_by = fields.Many2one('res.users', string='Conducted By', default=lambda self: self.env.user)

    total_items = fields.Integer(compute='_compute_stats', store=True, string='Total Items')
    checked_items = fields.Integer(compute='_compute_stats', store=True, string='Checked Items')
    completion_percentage = fields.Float(compute='_compute_stats', store=True, digits=(16, 2), string='Completion %')
    is_complete = fields.Boolean(compute='_compute_stats', store=True, string='Complete')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    findings = fields.Text(string='Findings/Notes')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    @api.depends('lines', 'lines.is_checked')
    def _compute_stats(self):
        for checklist in self:
            total = len(checklist.lines)
            checked = len(checklist.lines.filtered(lambda l: l.is_checked))
            checklist.total_items = total
            checklist.checked_items = checked
            if total > 0:
                checklist.completion_percentage = (checked / total) * 100
            else:
                checklist.completion_percentage = 0.0
            checklist.is_complete = checklist.completion_percentage == 100.0 and total > 0

    def action_start(self):
        for checklist in self:
            if checklist.state != 'draft':
                raise UserError(_("Checklist must be in draft to start."))
            checklist.state = 'in_progress'

    def action_complete(self):
        for checklist in self:
            if checklist.state in ('completed', 'cancelled'):
                raise UserError(_("Checklist is already completed/cancelled."))
            if not checklist.is_complete:
                raise UserError(_("All items must be checked before completion."))
            checklist.state = 'completed'

    def action_cancel(self):
        for checklist in self:
            checklist.state = 'cancelled'

    def action_generate_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/construction_checklist_report/' + str(self.id),
            'target': 'new',
        }


class ConstructionChecklistLine(models.Model):
    _name = 'construction.checklist.line'
    _description = 'Checklist Line'
    _order = 'checklist_id, sequence'

    checklist_id = fields.Many2one('construction.checklist', string='Checklist', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description', required=True)

    is_checked = fields.Boolean(string='Checked', default=False)
    checked_by = fields.Many2one('res.users', string='Checked By')
    checked_date = fields.Date(string='Checked Date')

    required_before_start = fields.Boolean(string='Required Before Start', default=False)
    notes = fields.Text(string='Notes')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    def action_check(self):
        for line in self:
            if not line.is_checked:
                line.is_checked = True
                line.checked_by = self.env.user
                line.checked_date = fields.Date.today()

    def action_uncheck(self):
        for line in self:
            if line.is_checked:
                line.is_checked = False
                line.checked_by = False
                line.checked_date = False
                