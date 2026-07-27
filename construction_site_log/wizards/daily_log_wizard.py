# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class ConstructionDailyLogRequestChanges(models.Model):
    """
    Wizard for requesting changes to a log.
    """
    _name = 'construction.daily.log.request.changes'
    _description = 'Request Changes Wizard'

    log_id = fields.Many2one(
        'construction.site.daily.log',
        string='Daily Log',
        required=True
    )

    message = fields.Text(
        string='Message',
        required=True,
        help='Describe the changes required'
    )

    changes_needed = fields.Text(
        string='Changes Needed',
        help='List of specific changes needed'
    )

    def action_send_request(self):
        """Send the change request."""
        self.ensure_one()

        if not self.log_id:
            raise ValidationError(_('No log selected.'))

        # Reset log to draft
        self.log_id.write({
            'state': 'draft',
            'submitted_date': False,
            'approval_date': False
        })

        # Send notification
        self.log_id.message_post(
            body=f"""
                <b>Changes Requested</b><br/>
                <b>Message:</b> {self.message}<br/>
                <b>Changes Needed:</b> {self.changes_needed or 'See message above'}<br/>
                <b>Requested by:</b> {self.env.user.name}
            """,
            subject=_('Changes Requested for Daily Log')
        )

        # Create activity for site supervisor
        if self.log_id.site_supervisor_id and self.log_id.site_supervisor_id.user_id:
            self.log_id.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.log_id.site_supervisor_id.user_id.id,
                summary=_('Changes Requested: %s') % self.log_id.name,
                note=self.message,
                date_deadline=fields.Date.today() + timedelta(days=2)
            )

        return {
            'type': 'ir.actions.act_window_close',
        }


class ToolboxTalkAttendeesWizard(models.Model):
    """
    Wizard for adding attendees to toolbox talk.
    """
    _name = 'toolbox.talk.attendees.wizard'
    _description = 'Add Attendees Wizard'

    talk_id = fields.Many2one(
        'construction.toolbox.talk',
        string='Toolbox Talk',
        required=True
    )

    attendee_ids = fields.Many2many(
        'hr.employee',
        'wizard_attendee_rel',
        string='Select Attendees',
        required=True
    )

    def action_add_attendees(self):
        """Add selected attendees to toolbox talk."""
        self.ensure_one()

        if not self.talk_id:
            raise ValidationError(_('No toolbox talk selected.'))

        # Add attendees
        current_attendees = self.talk_id.attendee_ids.ids
        new_attendees = self.attendee_ids.ids

        all_attendees = list(set(current_attendees + new_attendees))
        self.talk_id.write({
            'attendee_ids': [(6, 0, all_attendees)]
        })

        self.talk_id.message_post(
            body=_("""
                <b>Attendees Added</b><br/>
                Added %s attendees to the toolbox talk.
            """) % len(new_attendees),
            subject=_('Attendees Added')
        )

        return {
            'type': 'ir.actions.act_window_close',
        }


class IncidentAuthorityReportWizard(models.Model):
    """
    Wizard for reporting incident to authorities.
    """
    _name = 'incident.authority.report.wizard'
    _description = 'Report to Authorities Wizard'

    incident_id = fields.Many2one(
        'construction.incident.report',
        string='Incident',
        required=True
    )

    # REMOVED: authority_id field with invalid domain
    authority_name = fields.Char(
        string='Authority Name',
        required=True,
        help='Name of the regulatory authority'
    )

    report_number = fields.Char(
        string='Report Number',
        required=True
    )

    report_date = fields.Date(
        string='Report Date',
        required=True,
        default=fields.Date.today
    )

    description = fields.Text(
        string='Additional Information'
    )

    def action_submit_report(self):
        """Submit report to authority."""
        self.ensure_one()

        if not self.incident_id:
            raise ValidationError(_('No incident selected.'))

        # Update incident
        self.incident_id.write({
            'reported_to_authorities': True,
            'authority_report_number': self.report_number,
        })

        # Add note with authority name
        self.incident_id.message_post(
            body=f"""
                <b>Reported to Authority</b><br/>
                <b>Authority:</b> {self.authority_name}<br/>
                <b>Report Number:</b> {self.report_number}<br/>
                <b>Report Date:</b> {self.report_date}<br/>
                <b>Additional Info:</b> {self.description or 'N/A'}
            """,
            subject=_('Incident Reported to Authority')
        )

        return {
            'type': 'ir.actions.act_window_close',
        }


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
