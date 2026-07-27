# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class ConstructionActivityLog(models.Model):
    """
    Activity log for tracking all actions in the system.
    """
    _name = 'construction.activity.log'
    _description = 'Activity Log'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Activity',
        required=True
    )

    activity_type = fields.Selection([
        ('log_created', 'Log Created'),
        ('log_updated', 'Log Updated'),
        ('log_submitted', 'Log Submitted'),
        ('log_approved', 'Log Approved'),
        ('log_locked', 'Log Locked'),
        ('observation_created', 'Observation Created'),
        ('observation_updated', 'Observation Updated'),
        ('observation_closed', 'Observation Closed'),
        ('incident_created', 'Incident Created'),
        ('incident_updated', 'Incident Updated'),
        ('incident_resolved', 'Incident Resolved'),
        ('toolbox_talk_created', 'Toolbox Talk Created'),
        ('toolbox_talk_completed', 'Toolbox Talk Completed'),
        ('checklist_created', 'Checklist Created'),
        ('checklist_completed', 'Checklist Completed'),
        ('user_login', 'User Login'),
        ('user_logout', 'User Logout'),
        ('report_generated', 'Report Generated'),
    ], string='Activity Type',
        required=True)

    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
        required=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='user_id.employee_id',
        store=True
    )

    model = fields.Char(
        string='Model',
        help='Model name of the record'
    )

    res_id = fields.Integer(
        string='Record ID'
    )

    record_name = fields.Char(
        string='Record Name'
    )

    description = fields.Text(
        string='Description'
    )

    details = fields.Text(
        string='Details'
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.model
    def log_activity(self, activity_type, model, res_id, record_name, description='', details='', project_id=None):
        """Log an activity in the system."""
        vals = {
            'name': f"{activity_type} - {record_name}",
            'activity_type': activity_type,
            'user_id': self.env.user.id,
            'model': model,
            'res_id': res_id,
            'record_name': record_name,
            'description': description,
            'details': details,
            'project_id': project_id or self.env.context.get('default_project_id'),
            'company_id': self.env.company.id,
        }
        return self.create(vals)

    def action_view_record(self):
        """View the related record."""
        self.ensure_one()
        if self.model and self.res_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': self.model,
                'res_id': self.res_id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}


class ConstructionUserActivity(models.Model):
    """
    User activity summary.
    """
    _name = 'construction.user.activity'
    _description = 'User Activity Summary'
    _inherit = ['mail.thread']

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True
    )

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today
    )

    log_count = fields.Integer(
        string='Logs Created',
        default=0
    )

    observation_count = fields.Integer(
        string='Observations Created',
        default=0
    )

    incident_count = fields.Integer(
        string='Incidents Created',
        default=0
    )

    toolbox_talk_count = fields.Integer(
        string='Toolbox Talks',
        default=0
    )

    checklist_count = fields.Integer(
        string='Checklists Completed',
        default=0
    )

    total_activities = fields.Integer(
        compute='_compute_total_activities',
        string='Total Activities'
    )

    @api.depends('log_count', 'observation_count', 'incident_count',
                 'toolbox_talk_count', 'checklist_count')
    def _compute_total_activities(self):
        """Compute total activities."""
        for record in self:
            record.total_activities = (
                    record.log_count +
                    record.observation_count +
                    record.incident_count +
                    record.toolbox_talk_count +
                    record.checklist_count
            )

    @api.model
    def update_daily_activity(self, user_id=None):
        """Update or create daily activity record."""
        if not user_id:
            user_id = self.env.user.id

        today = fields.Date.today()
        activity = self.search([
            ('user_id', '=', user_id),
            ('date', '=', today)
        ], limit=1)

        if not activity:
            activity = self.create({
                'user_id': user_id,
                'date': today
            })

        return activity

    @api.model
    def increment_activity_count(self, user_id, activity_type, increment=1):
        """Increment a specific activity count."""
        activity = self.update_daily_activity(user_id)

        field_map = {
            'log': 'log_count',
            'observation': 'observation_count',
            'incident': 'incident_count',
            'toolbox_talk': 'toolbox_talk_count',
            'checklist': 'checklist_count',
        }

        field = field_map.get(activity_type)
        if field:
            current_value = getattr(activity, field, 0)
            setattr(activity, field, current_value + increment)

        return activity
    