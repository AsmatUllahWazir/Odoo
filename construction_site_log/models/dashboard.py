# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json


class ConstructionDashboard(models.Model):
    """
    Dashboard model for construction site analytics.
    """
    _name = 'construction.dashboard'
    _description = 'Construction Dashboard'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Dashboard Name',
        required=True,
        default=lambda self: _('Construction Dashboard')
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        help='Filter dashboard data by project'
    )

    date_from = fields.Date(
        string='Date From',
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )

    date_to = fields.Date(
        string='Date To',
        default=fields.Date.today
    )

    # Statistics Fields
    total_logs = fields.Integer(
        compute='_compute_stats',
        string='Total Logs'
    )

    submitted_logs = fields.Integer(
        compute='_compute_stats',
        string='Submitted Logs'
    )

    approved_logs = fields.Integer(
        compute='_compute_stats',
        string='Approved Logs'
    )

    total_observations = fields.Integer(
        compute='_compute_stats',
        string='Total Observations'
    )

    open_observations = fields.Integer(
        compute='_compute_stats',
        string='Open Observations'
    )

    critical_observations = fields.Integer(
        compute='_compute_stats',
        string='Critical Observations'
    )

    total_incidents = fields.Integer(
        compute='_compute_stats',
        string='Total Incidents'
    )

    open_incidents = fields.Integer(
        compute='_compute_stats',
        string='Open Incidents'
    )

    total_toolbox_talks = fields.Integer(
        compute='_compute_stats',
        string='Total Toolbox Talks'
    )

    total_workers = fields.Integer(
        compute='_compute_stats',
        string='Total Workers'
    )

    total_material_cost = fields.Float(
        compute='_compute_stats',
        string='Total Material Cost'
    )

    completion_rate = fields.Float(
        compute='_compute_stats',
        string='Log Completion Rate (%)'
    )

    safety_score = fields.Float(
        compute='_compute_stats',
        string='Safety Score'
    )

    # Data for Charts
    logs_by_date = fields.Text(
        compute='_compute_chart_data',
        string='Logs by Date'
    )

    observations_by_severity = fields.Text(
        compute='_compute_chart_data',
        string='Observations by Severity'
    )

    incidents_by_type = fields.Text(
        compute='_compute_chart_data',
        string='Incidents by Type'
    )

    manpower_by_category = fields.Text(
        compute='_compute_chart_data',
        string='Manpower by Category'
    )

    # Dynamic filters
    domain = fields.Char(
        string='Domain',
        default='[]'
    )

    def _compute_stats(self):
        """Compute dashboard statistics."""
        for record in self:
            domain = []
            if record.project_id:
                domain.append(('project_id', '=', record.project_id.id))
            if record.date_from:
                domain.append(('date', '>=', record.date_from))
            if record.date_to:
                domain.append(('date', '<=', record.date_to))

            # Daily Logs
            Log = self.env['construction.site.daily.log']
            logs = Log.search(domain)
            record.total_logs = len(logs)
            record.submitted_logs = len(logs.filtered(lambda l: l.state == 'submitted'))
            record.approved_logs = len(logs.filtered(lambda l: l.state in ['approved', 'locked']))
            record.total_workers = sum(logs.mapped('total_workers'))
            record.total_material_cost = sum(logs.mapped('total_material_value'))
            record.completion_rate = (record.approved_logs / record.total_logs * 100) if record.total_logs > 0 else 0

            # Safety Observations
            Obs = self.env['construction.safety.observation']
            obs = Obs.search(domain)
            record.total_observations = len(obs)
            record.open_observations = len(obs.filtered(lambda o: o.status in ['open', 'in_progress']))
            record.critical_observations = len(obs.filtered(lambda o: o.severity in ['high', 'critical']))

            # Incidents
            Inc = self.env['construction.incident.report']
            incidents = Inc.search(domain)
            record.total_incidents = len(incidents)
            record.open_incidents = len(incidents.filtered(lambda i: i.status in ['draft', 'under_investigation']))

            # Toolbox Talks
            Talk = self.env['construction.toolbox.talk']
            record.total_toolbox_talks = len(Talk.search(domain))

            # Safety Score
            record.safety_score = self._compute_safety_score(record)

    def _compute_safety_score(self, record):
        """Compute safety score based on various metrics."""
        score = 100.0

        # Deduct for open observations
        score -= record.open_observations * 2

        # Deduct for critical observations
        score -= record.critical_observations * 5

        # Deduct for open incidents
        score -= record.open_incidents * 10

        # Add for toolbox talks
        score += record.total_toolbox_talks * 0.5

        # Ensure score is between 0 and 100
        return max(0, min(100, score))

    def _compute_chart_data(self):
        """Compute data for charts."""
        for record in self:
            domain = []
            if record.project_id:
                domain.append(('project_id', '=', record.project_id.id))
            if record.date_from:
                domain.append(('date', '>=', record.date_from))
            if record.date_to:
                domain.append(('date', '<=', record.date_to))

            # Logs by Date
            logs = self.env['construction.site.daily.log'].search(domain)
            date_data = {}
            for log in logs:
                date_key = log.date.strftime('%Y-%m-%d')
                if date_key not in date_data:
                    date_data[date_key] = {'draft': 0, 'submitted': 0, 'approved': 0, 'locked': 0}
                date_data[date_key][log.state] = date_data[date_key].get(log.state, 0) + 1
            record.logs_by_date = json.dumps(date_data)

            # Observations by Severity
            obs = self.env['construction.safety.observation'].search(domain)
            severity_data = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
            for obs_record in obs:
                severity_data[obs_record.severity] = severity_data.get(obs_record.severity, 0) + 1
            record.observations_by_severity = json.dumps(severity_data)

            # Incidents by Type
            incidents = self.env['construction.incident.report'].search(domain)
            type_data = {}
            for incident in incidents:
                type_data[incident.incident_type] = type_data.get(incident.incident_type, 0) + 1
            record.incidents_by_type = json.dumps(type_data)

            # Manpower by Category
            manpower = self.env['construction.site.daily.log.manpower'].search([('log_id.project_id', 'in', domain)])
            category_data = {}
            for line in manpower:
                category_data[line.category] = category_data.get(line.category, 0) + line.actual_workers
            record.manpower_by_category = json.dumps(category_data)

    def action_refresh(self):
        """Refresh dashboard data."""
        self._compute_stats()
        self._compute_chart_data()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_logs(self):
        """Open filtered daily logs."""
        self.ensure_one()
        domain = []
        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Daily Logs'),
            'res_model': 'construction.site.daily.log',
            'view_mode': 'tree,form',
            'domain': domain,
        }

    def action_open_observations(self):
        """Open filtered safety observations."""
        self.ensure_one()
        domain = []
        if self.project_id:
            domain.append(('project_id', '=', self.project_id.id))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Safety Observations'),
            'res_model': 'construction.safety.observation',
            'view_mode': 'tree,form',
            'domain': domain,
        }


class ConstructionDashboardWidget(models.Model):
    """
    Dashboard widget configuration.
    """
    _name = 'construction.dashboard.widget'
    _description = 'Dashboard Widget'
    _order = 'sequence, id'

    dashboard_id = fields.Many2one(
        'construction.dashboard',
        string='Dashboard',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string='Widget Name',
        required=True
    )

    widget_type = fields.Selection([
        ('stat', 'Statistics'),
        ('chart', 'Chart'),
        ('list', 'List'),
        ('calendar', 'Calendar'),
        ('kanban', 'Kanban')
    ], string='Widget Type',
        required=True,
        default='stat')

    model = fields.Char(
        string='Model',
        help='Model to display data from'
    )

    domain = fields.Char(
        string='Domain',
        default='[]'
    )

    fields_display = fields.Char(
        string='Fields to Display',
        help='Comma-separated list of fields'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    width = fields.Selection([
        ('small', 'Small'),
        ('medium', 'Medium'),
        ('large', 'Large'),
        ('full', 'Full Width')
    ], string='Width',
        default='medium')

    height = fields.Integer(
        string='Height (px)',
        default=300
    )

    visible = fields.Boolean(
        string='Visible',
        default=True
    )
