# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
from io import BytesIO
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ConstructionReportWizard(models.Model):
    """
    Report generation wizard.
    """
    _name = 'construction.report.wizard'
    _description = 'Report Wizard'

    log_id = fields.Many2one(
        'construction.site.daily.log',
        string='Daily Log',
        required=True
    )

    report_type = fields.Selection([
        ('daily', 'Daily Log'),
        ('weekly', 'Weekly Summary'),
        ('monthly', 'Monthly Summary'),
        ('safety', 'Safety Report'),
        ('incident', 'Incident Report'),
        ('custom', 'Custom Report')
    ], string='Report Type',
        required=True,
        default='daily')

    date_from = fields.Date(
        string='Date From'
    )

    date_to = fields.Date(
        string='Date To'
    )

    include_photos = fields.Boolean(
        string='Include Photos',
        default=True
    )

    include_signatures = fields.Boolean(
        string='Include Signatures',
        default=True
    )

    format = fields.Selection([
        ('pdf', 'PDF'),
        ('html', 'HTML'),
        ('excel', 'Excel')
    ], string='Format',
        required=True,
        default='pdf')

    language = fields.Selection(
        selection=lambda self: self._get_languages(),
        string='Language',
        default='en_US'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.model
    def _get_languages(self):
        """Get available languages."""
        return self.env['res.lang'].get_installed()

    def action_generate_report(self):
        """Generate the selected report."""
        self.ensure_one()

        if self.report_type == 'daily':
            return self._generate_daily_report()
        elif self.report_type == 'weekly':
            return self._generate_weekly_report()
        elif self.report_type == 'monthly':
            return self._generate_monthly_report()
        elif self.report_type == 'safety':
            return self._generate_safety_report()
        elif self.report_type == 'incident':
            return self._generate_incident_report()
        else:
            return self._generate_custom_report()

    def _generate_daily_report(self):
        """Generate daily report."""
        self.ensure_one()
        return self.env.ref('construction_site_log.action_report_construction_daily_log').report_action(self.log_id)

    def _generate_weekly_report(self):
        """Generate weekly summary report."""
        self.ensure_one()

        WeeklyReport = self.env['construction.weekly.report']

        date_from = self.date_from or (fields.Date.today() - timedelta(days=7))
        date_to = self.date_to or fields.Date.today()

        existing = WeeklyReport.search([
            ('project_id', '=', self.log_id.project_id.id),
            ('date_from', '=', date_from),
            ('date_to', '=', date_to)
        ], limit=1)

        if existing:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'construction.weekly.report',
                'res_id': existing.id,
                'view_mode': 'form',
                'target': 'current',
            }

        logs = self.env['construction.site.daily.log'].search([
            ('project_id', '=', self.log_id.project_id.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to)
        ])

        weekly_report = WeeklyReport.create({
            'name': f"Weekly Report - Week {fields.Date.today().isocalendar()[1]}",
            'project_id': self.log_id.project_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'log_ids': [(6, 0, logs.ids)]
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.weekly.report',
            'res_id': weekly_report.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _generate_monthly_report(self):
        """Generate monthly summary report."""
        self.ensure_one()

        MonthlyReport = self.env['construction.monthly.report']

        date_from = self.date_from or fields.Date.today().replace(day=1)
        month = str(date_from.month)
        year = date_from.year

        existing = MonthlyReport.search([
            ('project_id', '=', self.log_id.project_id.id),
            ('month', '=', month),
            ('year', '=', year)
        ], limit=1)

        if existing:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'construction.monthly.report',
                'res_id': existing.id,
                'view_mode': 'form',
                'target': 'current',
            }

        monthly_report = MonthlyReport.create({
            'name': f"Monthly Report - {date_from.strftime('%B %Y')}",
            'project_id': self.log_id.project_id.id,
            'month': month,
            'year': year,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.monthly.report',
            'res_id': monthly_report.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _generate_safety_report(self):
        """Generate safety report."""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.safety.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.log_id.project_id.id,
                'default_date_from': self.date_from or (fields.Date.today() - timedelta(days=30)),
                'default_date_to': self.date_to or fields.Date.today(),
            }
        }

    def _generate_incident_report(self):
        """Generate incident report."""
        self.ensure_one()

        incidents = self.log_id.incident_report_ids

        if not incidents:
            raise ValidationError(_('No incidents found for this log.'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.incident.report',
            'res_id': incidents[0].id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _generate_custom_report(self):
        """Generate custom report."""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.custom.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_project_id': self.log_id.project_id.id,
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
                'default_log_id': self.log_id.id,
            }
        }


class ConstructionWeeklyReport(models.Model):
    """
    Weekly summary report.
    """
    _name = 'construction.weekly.report'
    _description = 'Weekly Report'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Report Name',
        required=True,
        default=lambda self: f"Weekly Report - Week {datetime.now().isocalendar()[1]}"
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True
    )

    date_from = fields.Date(
        string='Date From',
        required=True
    )

    date_to = fields.Date(
        string='Date To',
        required=True
    )

    log_ids = fields.Many2many(
        'construction.site.daily.log',
        'weekly_report_log_rel',
        'weekly_report_id',
        'log_id',
        string='Daily Logs'
    )

    # REMOVED: monthly_report_id - completely removed

    total_logs = fields.Integer(
        compute='_compute_report_stats',
        string='Total Logs',
        store=False
    )

    total_observations = fields.Integer(
        compute='_compute_report_stats',
        string='Total Observations',
        store=False
    )

    total_incidents = fields.Integer(
        compute='_compute_report_stats',
        string='Total Incidents',
        store=False
    )

    total_toolbox_talks = fields.Integer(
        compute='_compute_report_stats',
        string='Total Toolbox Talks',
        store=False
    )

    average_workers = fields.Float(
        compute='_compute_report_stats',
        string='Average Workers',
        store=False
    )

    total_material_cost = fields.Float(
        compute='_compute_report_stats',
        string='Total Material Cost',
        store=False
    )

    safety_score = fields.Float(
        compute='_compute_report_stats',
        string='Safety Score',
        store=False
    )

    summary = fields.Text(
        compute='_compute_report_stats',
        string='Summary',
        store=False
    )

    @api.depends('log_ids')
    def _compute_report_stats(self):
        """Compute report statistics."""
        for record in self:
            logs = record.log_ids

            record.total_logs = len(logs)
            record.total_observations = sum(len(log.safety_observation_ids) for log in logs)
            record.total_incidents = sum(len(log.incident_report_ids) for log in logs)
            record.total_toolbox_talks = sum(len(log.toolbox_talk_ids) for log in logs)
            record.average_workers = sum(log.total_workers for log in logs) / len(logs) if logs else 0
            record.total_material_cost = sum(log.total_material_value for log in logs)

            # Calculate safety score
            score = 100
            for log in logs:
                if log.risk_level in ['high', 'critical']:
                    score -= 5
                if len(log.safety_observation_ids) > 3:
                    score -= 2
                if len(log.incident_report_ids) > 0:
                    score -= 10
                if log.toolbox_talk_ids:
                    score += 1

            record.safety_score = max(0, min(100, score))

            record.summary = f"""
Weekly Safety Performance Summary:
- Total Logs: {record.total_logs}
- Total Observations: {record.total_observations}
- Total Incidents: {record.total_incidents}
- Total Toolbox Talks: {record.total_toolbox_talks}
- Average Workers: {record.average_workers:.1f}
- Total Material Cost: {record.total_material_cost:.2f}
- Safety Score: {record.safety_score:.1f}%
"""


class ConstructionMonthlyReport(models.Model):
    """
    Monthly summary report.
    """
    _name = 'construction.monthly.report'
    _description = 'Monthly Report'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Report Name',
        required=True,
        default=lambda self: f"Monthly Report - {datetime.now().strftime('%B %Y')}"
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True
    )

    month = fields.Selection(
        [(str(i), datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)],
        string='Month',
        required=True
    )

    year = fields.Integer(
        string='Year',
        required=True,
        default=datetime.now().year
    )

    # REMOVED: weekly_report_ids One2many - completely removed

    total_logs = fields.Integer(
        compute='_compute_monthly_stats',
        string='Total Logs',
        store=False
    )

    total_observations = fields.Integer(
        compute='_compute_monthly_stats',
        string='Total Observations',
        store=False
    )

    total_incidents = fields.Integer(
        compute='_compute_monthly_stats',
        string='Total Incidents',
        store=False
    )

    total_toolbox_talks = fields.Integer(
        compute='_compute_monthly_stats',
        string='Total Toolbox Talks',
        store=False
    )

    average_workers = fields.Float(
        compute='_compute_monthly_stats',
        string='Average Workers',
        store=False
    )

    total_material_cost = fields.Float(
        compute='_compute_monthly_stats',
        string='Total Material Cost',
        store=False
    )

    safety_score = fields.Float(
        compute='_compute_monthly_stats',
        string='Safety Score',
        store=False
    )

    summary = fields.Text(
        compute='_compute_monthly_stats',
        string='Summary',
        store=False
    )

    @api.depends('project_id', 'month', 'year')
    def _compute_monthly_stats(self):
        """Compute monthly statistics directly from logs."""
        for record in self:
            # Get all logs for the month directly
            logs = self.env['construction.site.daily.log'].search([
                ('project_id', '=', record.project_id.id),
                ('date', '>=', f"{record.year}-{int(record.month):02d}-01"),
                ('date', '<=', f"{record.year}-{int(record.month):02d}-31")
            ])

            record.total_logs = len(logs)
            record.total_observations = sum(len(log.safety_observation_ids) for log in logs)
            record.total_incidents = sum(len(log.incident_report_ids) for log in logs)
            record.total_toolbox_talks = sum(len(log.toolbox_talk_ids) for log in logs)
            record.average_workers = sum(log.total_workers for log in logs) / len(logs) if logs else 0
            record.total_material_cost = sum(log.total_material_value for log in logs)

            # Calculate safety score
            score = 100
            for log in logs:
                if log.risk_level in ['high', 'critical']:
                    score -= 5
                if len(log.safety_observation_ids) > 3:
                    score -= 2
                if len(log.incident_report_ids) > 0:
                    score -= 10
                if log.toolbox_talk_ids:
                    score += 1

            record.safety_score = max(0, min(100, score))

            month_name = datetime(int(record.year), int(record.month), 1).strftime('%B')
            record.summary = f"""
Monthly Safety Performance Summary ({month_name} {record.year}):

Total Logs: {record.total_logs}
Total Observations: {record.total_observations}
Total Incidents: {record.total_incidents}
Total Toolbox Talks: {record.total_toolbox_talks}
Average Workers: {record.average_workers:.1f}
Total Material Cost: {record.total_material_cost:.2f}
Safety Score: {record.safety_score:.1f}%
"""


class ConstructionSafetyReport(models.Model):
    """
    Safety report summary.
    """
    _name = 'construction.safety.report'
    _description = 'Safety Report'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Report Name',
        required=True,
        default=lambda self: f"Safety Report - {fields.Date.today()}"
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True
    )

    date_from = fields.Date(
        string='Date From',
        required=True
    )

    date_to = fields.Date(
        string='Date To',
        required=True
    )

    total_observations = fields.Integer(
        string='Total Observations'
    )

    open_observations = fields.Integer(
        string='Open Observations'
    )

    critical_observations = fields.Integer(
        string='Critical Observations'
    )

    total_incidents = fields.Integer(
        string='Total Incidents'
    )

    resolved_incidents = fields.Integer(
        string='Resolved Incidents'
    )

    total_toolbox_talks = fields.Integer(
        string='Total Toolbox Talks'
    )

    safety_score = fields.Float(
        string='Safety Score'
    )

    summary = fields.Text(
        string='Summary'
    )

    observations_summary = fields.Text(
        string='Observations Summary'
    )

    incidents_summary = fields.Text(
        string='Incidents Summary'
    )

    @api.model
    def create(self, vals):
        """Override create to compute statistics."""
        result = super().create(vals)
        result._compute_safety_stats()
        return result

    def write(self, vals):
        """Override write to recompute statistics."""
        result = super().write(vals)
        if vals.get('project_id') or vals.get('date_from') or vals.get('date_to'):
            self._compute_safety_stats()
        return result

    def _compute_safety_stats(self):
        """Compute safety statistics."""
        for record in self:
            domain = [
                ('project_id', '=', record.project_id.id),
                ('date', '>=', record.date_from),
                ('date', '<=', record.date_to)
            ]

            # Observations
            Obs = self.env['construction.safety.observation']
            observations = Obs.search(domain)
            record.total_observations = len(observations)
            record.open_observations = len(observations.filtered(lambda o: o.status in ['open', 'in_progress']))
            record.critical_observations = len(observations.filtered(lambda o: o.severity in ['high', 'critical']))

            # Incidents
            Inc = self.env['construction.incident.report']
            incidents = Inc.search(domain)
            record.total_incidents = len(incidents)
            record.resolved_incidents = len(incidents.filtered(lambda i: i.status in ['resolved', 'closed']))

            # Toolbox Talks
            Talk = self.env['construction.toolbox.talk']
            record.total_toolbox_talks = len(Talk.search(domain))

            # Safety Score
            score = 100
            score -= record.open_observations * 2
            score -= record.critical_observations * 5
            score -= (record.total_incidents - record.resolved_incidents) * 3
            score += record.total_toolbox_talks * 1
            record.safety_score = max(0, min(100, score))

            # Summaries
            record.observations_summary = '\n'.join([
                f"- {obs.name}: {obs.description[:100]}..."
                for obs in observations[:10]
            ]) if observations else 'No observations recorded.'

            record.incidents_summary = '\n'.join([
                f"- {inc.name}: {inc.incident_type} - {inc.status}"
                for inc in incidents[:10]
            ]) if incidents else 'No incidents recorded.'

            record.summary = f"""
Safety Performance Summary from {record.date_from} to {record.date_to}:

Observations:
- Total: {record.total_observations}
- Open: {record.open_observations}
- Critical: {record.critical_observations}

Incidents:
- Total: {record.total_incidents}
- Resolved: {record.resolved_incidents}

Toolbox Talks: {record.total_toolbox_talks}
Safety Score: {record.safety_score:.1f}%
"""


class ConstructionCustomReport(models.Model):
    """
    Custom report generation.
    """
    _name = 'construction.custom.report'
    _description = 'Custom Report'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Report Name',
        required=True,
        default=lambda self: f"Custom Report - {fields.Date.today()}"
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project'
    )

    log_id = fields.Many2one(
        'construction.site.daily.log',
        string='Daily Log'
    )

    date_from = fields.Date(
        string='Date From'
    )

    date_to = fields.Date(
        string='Date To'
    )

    include_manpower = fields.Boolean(
        string='Include Manpower',
        default=True
    )

    include_materials = fields.Boolean(
        string='Include Materials',
        default=True
    )

    include_progress = fields.Boolean(
        string='Include Progress',
        default=True
    )

    include_safety = fields.Boolean(
        string='Include Safety',
        default=True
    )

    include_photos = fields.Boolean(
        string='Include Photos',
        default=True
    )

    format = fields.Selection([
        ('pdf', 'PDF'),
        ('html', 'HTML'),
        ('excel', 'Excel')
    ], string='Format',
        default='pdf')

    generated_report = fields.Binary(
        string='Generated Report',
        attachment=True
    )

    generated_filename = fields.Char(
        string='Filename'
    )

    def action_generate(self):
        """Generate custom report."""
        self.ensure_one()

        if self.log_id:
            return self.env.ref('construction_site_log.action_report_construction_daily_log').report_action(self.log_id)
        else:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'construction.dashboard',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_project_id': self.project_id.id,
                    'default_date_from': self.date_from,
                    'default_date_to': self.date_to,
                }
            }
