# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class ConstructionSafetyObservation(models.Model):
    """
    Safety observations model for tracking site safety issues.
    """
    _name = 'construction.safety.observation'
    _description = 'Construction Safety Observation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, severity desc, id desc'

    # ========== Basic Fields ==========
    name = fields.Char(
        string='Observation Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )

    daily_log_id = fields.Many2one(
        'construction.site.daily.log',
        string='Daily Log',
        ondelete='set null',
        help='Link to the daily log if observed during routine logging'
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        tracking=True
    )

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )

    # ========== Severity and Location ==========
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Severity',
        required=True,
        default='medium',
        tracking=True)

    severity_color = fields.Integer(
        compute='_compute_severity_color',
        string='Severity Color'
    )

    location = fields.Char(
        string='Location',
        required=True,
        tracking=True,
        help='Specific location on site where observation was made'
    )

    location_detailed = fields.Text(
        string='Detailed Location',
        help='Additional details about the location'
    )

    # ========== Description and Actions ==========
    description = fields.Text(
        string='Description',
        required=True,
        tracking=True,
        help='Detailed description of the safety observation'
    )

    immediate_action = fields.Text(
        string='Immediate Action Taken',
        help='Any immediate action taken to address the issue'
    )

    corrective_action = fields.Text(
        string='Corrective Action',
        tracking=True,
        help='Long-term corrective action required'
    )

    # ========== People ==========
    responsible_person_id = fields.Many2one(
        'hr.employee',
        string='Responsible Person',
        tracking=True,
        help='Person responsible for resolving this observation'
    )

    reported_by_id = fields.Many2one(
        'res.users',
        string='Reported By',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True
    )

    verified_by_id = fields.Many2one(
        'hr.employee',
        string='Verified By',
        tracking=True,
        help='Person who verified the observation'
    )

    # ========== Dates ==========
    due_date = fields.Date(
        string='Due Date',
        tracking=True,
        help='Date by which corrective action should be completed'
    )

    closed_date = fields.Datetime(
        string='Closed Date',
        readonly=True,
        copy=False,
        tracking=True
    )

    in_progress_date = fields.Datetime(
        string='In Progress Date',
        readonly=True,
        copy=False,
        tracking=True
    )

    # ========== Status ==========
    status = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed')
    ], string='Status',
        default='open',
        tracking=True,
        required=True)

    status_color = fields.Integer(
        compute='_compute_status_color',
        string='Status Color'
    )

    # ========== Days Open ==========
    days_open = fields.Integer(
        compute='_compute_days_open',
        string='Days Open',
        store=True,
        help='Number of days the observation has been open'
    )

    is_overdue = fields.Boolean(
        compute='_compute_is_overdue',
        string='Is Overdue',
        store=True,
        help='Check if the observation is overdue'
    )

    # ========== Attachments ==========
    photo_attachment_ids = fields.Many2many(
        'ir.attachment',
        'safety_observation_photo_rel',
        'observation_id',
        'attachment_id',
        string='Photos'
    )

    document_attachment_ids = fields.Many2many(
        'ir.attachment',
        'safety_observation_doc_rel',
        'observation_id',
        'attachment_id',
        string='Documents'
    )

    # ========== Notes ==========
    notes = fields.Text(
        string='Notes'
    )

    # ========== Company ==========
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # ========== Compute Methods ==========

    @api.depends('severity')
    def _compute_severity_color(self):
        """Compute color for severity level."""
        color_map = {
            'low': 10,  # Green
            'medium': 9,  # Yellow
            'high': 8,  # Orange
            'critical': 7,  # Red
        }
        for record in self:
            record.severity_color = color_map.get(record.severity, 10)

    @api.depends('status')
    def _compute_status_color(self):
        """Compute color for status."""
        color_map = {
            'open': 7,  # Red
            'in_progress': 8,  # Orange
            'closed': 10,  # Green
        }
        for record in self:
            record.status_color = color_map.get(record.status, 10)

    @api.depends('status', 'closed_date', 'create_date')
    def _compute_days_open(self):
        """Compute number of days the observation has been open."""
        for record in self:
            if record.status == 'closed' and record.closed_date:
                delta = record.closed_date - record.create_date
                record.days_open = delta.days if delta else 0
            elif record.create_date:
                delta = fields.Datetime.now() - record.create_date
                record.days_open = delta.days if delta else 0
            else:
                record.days_open = 0

    @api.depends('status', 'due_date', 'days_open')
    def _compute_is_overdue(self):
        """Check if the observation is overdue."""
        for record in self:
            if record.status != 'closed' and record.due_date:
                record.is_overdue = fields.Date.today() > record.due_date
            else:
                record.is_overdue = False

    # ========== CRUD Overrides ==========

    @api.model
    def create(self, vals):
        """Override create to generate sequence number and validate."""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'construction.safety.observation') or _('New')

        # Set default due date if not provided
        if not vals.get('due_date') and vals.get('severity') in ['high', 'critical']:
            vals['due_date'] = fields.Date.today() + timedelta(days=7)
        elif not vals.get('due_date'):
            vals['due_date'] = fields.Date.today() + timedelta(days=14)

        return super().create(vals)

    def write(self, vals):
        """Override write to add tracking and validation."""
        if 'status' in vals:
            if vals['status'] == 'closed' and not self.corrective_action:
                # Check each record being closed
                for record in self:
                    if not record.corrective_action:
                        raise ValidationError(
                            _('Please provide a corrective action before closing observation %s.')
                            % record.name
                        )

        return super().write(vals)

    def unlink(self):
        """Prevent deletion of non-open observations."""
        for record in self:
            if record.status != 'open':
                raise ValidationError(
                    _('You cannot delete a safety observation that is not in open status.')
                )
        return super().unlink()

    # ========== Action Methods ==========

    def action_mark_in_progress(self):
        """Mark observation as in progress."""
        self.ensure_one()

        if self.status == 'closed':
            raise ValidationError(_('Closed observations cannot be reopened.'))

        self.write({
            'status': 'in_progress',
            'in_progress_date': fields.Datetime.now()
        })

        self.message_post(
            body=_("""
                <b>Safety Observation Updated</b><br/>
                Observation: %s<br/>
                Status changed to: In Progress<br/>
                Updated by: %s
            """) % (
                self.name,
                self.env.user.name
            ),
            subject=_('Status Updated - In Progress')
        )

    def action_close(self):
        """Close the observation."""
        self.ensure_one()

        if not self.corrective_action:
            raise ValidationError(
                _('Please provide a corrective action before closing.')
            )

        if self.status == 'closed':
            raise ValidationError(_('This observation is already closed.'))

        self.write({
            'status': 'closed',
            'closed_date': fields.Datetime.now()
        })

        self.message_post(
            body=_("""
                <b>Safety Observation Closed</b><br/>
                Observation: %s<br/>
                Closed by: %s<br/>
                Corrective Action: %s
            """) % (
                self.name,
                self.env.user.name,
                self.corrective_action
            ),
            subject=_('Observation Closed')
        )

    def action_assign_to_me(self):
        """Assign the observation to the current user."""
        self.ensure_one()

        if not self.env.user.employee_id:
            raise ValidationError(_('Your user does not have an associated employee record.'))

        self.write({'responsible_person_id': self.env.user.employee_id.id})

        self.message_post(
            body=_("""
                <b>Safety Observation Assigned</b><br/>
                Observation: %s<br/>
                Assigned to: %s
            """) % (
                self.name,
                self.env.user.name
            ),
            subject=_('Observation Assigned')
        )

    def action_escalate(self):
        """Escalate the observation to a higher severity."""
        self.ensure_one()

        severity_order = {
            'low': 'medium',
            'medium': 'high',
            'high': 'critical',
        }

        if self.severity == 'critical':
            raise ValidationError(_('This observation is already at critical severity.'))

        new_severity = severity_order.get(self.severity)

        self.write({
            'severity': new_severity,
            'due_date': fields.Date.today() + timedelta(days=3),
        })

        self.message_post(
            body=_("""
                <b>Safety Observation Escalated</b><br/>
                Observation: %s<br/>
                New Severity: %s<br/>
                Escalated by: %s
            """) % (
                self.name,
                self.get_severity_selection(new_severity),
                self.env.user.name
            ),
            subject=_('Observation Escalated')
        )

    def action_create_task(self):
        """Create a project task from this observation."""
        self.ensure_one()

        task_vals = {
            'name': f"Safety: {self.name}",
            'project_id': self.project_id.id,
            'description': f"""
                <b>Safety Observation Details:</b><br/>
                Reference: {self.name}<br/>
                Severity: {self.get_severity_selection(self.severity)}<br/>
                Location: {self.location}<br/>
                Description: {self.description}<br/>
                Corrective Action: {self.corrective_action or 'Not defined yet'}<br/>
                <a href="#" data-oe-model="construction.safety.observation" data-oe-id="{self.id}">View Original Observation</a>
            """,
            'date_deadline': self.due_date,
            'user_ids': [(4,
                          self.responsible_person_id.user_id.id)] if self.responsible_person_id and self.responsible_person_id.user_id else False,
        }

        task = self.env['project.task'].create(task_vals)

        self.message_post(
            body=_("""
                <b>Project Task Created</b><br/>
                Task: <a href="#" data-oe-model="project.task" data-oe-id="%d">%s</a>
            """) % (task.id, task.name),
            subject=_('Task Created')
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': task.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ========== Helper Methods ==========

    def get_severity_selection(self, severity):
        """Helper to get severity display name."""
        selections = dict(self._fields['severity'].selection)
        return selections.get(severity, severity)

    # ========== Statistics Methods ==========

    @api.model
    def get_observation_stats(self, project_id=None):
        """Get statistics about safety observations."""
        domain = []
        if project_id:
            domain.append(('project_id', '=', project_id))

        total = self.search_count(domain)
        open_count = self.search_count(domain + [('status', '=', 'open')])
        in_progress_count = self.search_count(domain + [('status', '=', 'in_progress')])
        closed_count = self.search_count(domain + [('status', '=', 'closed')])

        high_severity = self.search_count(domain + [('severity', 'in', ['high', 'critical'])])

        return {
            'total': total,
            'open': open_count,
            'in_progress': in_progress_count,
            'closed': closed_count,
            'high_severity': high_severity,
            'completion_rate': (closed_count / total * 100) if total > 0 else 0,
        }

    # ========== Constraints ==========

    @api.constrains('severity', 'due_date')
    def _check_due_date(self):
        """Validate due date based on severity."""
        for record in self:
            if record.severity in ['high', 'critical']:
                if record.due_date and record.due_date > fields.Date.today() + timedelta(days=14):
                    raise ValidationError(
                        _('For high and critical observations, due date must be within 14 days.')
                    )

    @api.constrains('date')
    def _check_future_date(self):
        """Prevent future dates."""
        for record in self:
            if record.date and record.date > fields.Date.today():
                raise ValidationError(_('Observation date cannot be in the future.'))

    @api.constrains('responsible_person_id')
    def _check_responsible_person(self):
        """Validate responsible person is assigned for high severity."""
        for record in self:
            if record.severity in ['high', 'critical'] and not record.responsible_person_id:
                raise ValidationError(
                    _('High and critical observations must have a responsible person assigned.')
                )

    # ========== Automated Actions ==========

    def _auto_escalate_overdue(self):
        """Automatically escalate overdue observations."""
        overdue_observations = self.search([
            ('status', 'in', ['open', 'in_progress']),
            ('is_overdue', '=', True),
            ('severity', '!=', 'critical')
        ])

        for obs in overdue_observations:
            if obs.severity == 'low':
                obs.write({'severity': 'medium'})
            elif obs.severity == 'medium':
                obs.write({'severity': 'high'})
            elif obs.severity == 'high':
                obs.write({'severity': 'critical'})

            obs.message_post(
                body=_("""
                    <b>Auto-Escalation Notice</b><br/>
                    This observation was automatically escalated due to being overdue.
                    New Severity: %s
                """) % obs.get_severity_selection(obs.severity),
                subject=_('Observation Auto-Escalated')
            )

        _logger.info(f"Auto-escalated {len(overdue_observations)} overdue observations")


class ConstructionSafetyObservationHistory(models.Model):
    """
    History tracking for safety observations.
    """
    _name = 'construction.safety.observation.history'
    _description = 'Safety Observation History'
    _order = 'create_date desc'

    observation_id = fields.Many2one(
        'construction.safety.observation',
        string='Observation',
        required=True,
        ondelete='cascade'
    )

    field_name = fields.Char(
        string='Field Name',
        required=True
    )

    old_value = fields.Text(
        string='Old Value'
    )

    new_value = fields.Text(
        string='New Value'
    )

    changed_by_id = fields.Many2one(
        'res.users',
        string='Changed By',
        default=lambda self: self.env.user
    )

    change_date = fields.Datetime(
        string='Change Date',
        default=fields.Datetime.now
    )
