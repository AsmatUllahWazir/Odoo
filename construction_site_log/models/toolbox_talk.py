# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ConstructionToolboxTalk(models.Model):
    """
    Toolbox talk model for recording safety meetings.
    """
    _name = 'construction.toolbox.talk'
    _description = 'Construction Toolbox Talk'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    # ========== Basic Fields ==========
    name = fields.Char(
        string='Toolbox Talk Subject',
        required=True,
        tracking=True,
        help='Main subject/topic of the toolbox talk'
    )

    daily_log_id = fields.Many2one(
        'construction.site.daily.log',
        string='Daily Log',
        ondelete='set null',
        help='Link to the daily log if conducted on that day'
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

    start_time = fields.Float(
        string='Start Time',
        help='Start time in decimal format (e.g., 8.5 = 08:30)'
    )

    end_time = fields.Float(
        string='End Time',
        compute='_compute_times',
        store=True,
        help='End time calculated from duration'
    )

    duration_hours = fields.Float(
        string='Duration (Hours)',
        required=True,
        default=0.5,
        help='Duration of the toolbox talk in hours'
    )

    # ========== Content ==========
    topic = fields.Text(
        string='Topic',
        required=True,
        tracking=True,
        help='Detailed topic of the toolbox talk'
    )

    key_points = fields.Text(
        string='Key Points Discussed',
        help='Main points covered during the talk'
    )

    material_used = fields.Text(
        string='Material Used',
        help='Any materials, presentations, or equipment used'
    )

    # ========== People ==========
    presenter_id = fields.Many2one(
        'hr.employee',
        string='Presenter',
        required=True,
        tracking=True
    )

    attendee_ids = fields.Many2many(
        'hr.employee',
        'toolbox_talk_attendee_rel',
        'talk_id',
        'employee_id',
        string='Attendees',
        help='Employees who attended the toolbox talk'
    )

    attendee_count = fields.Integer(
        compute='_compute_attendee_count',
        string='Number of Attendees',
        store=True
    )

    signatories = fields.Text(
        string='Signatories',
        help='List of attendees who signed'
    )

    signatory_count = fields.Integer(
        compute='_compute_signatory_count',
        string='Number of Signatories',
        store=True
    )

    # ========== Status ==========
    state = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status',
        default='planned',
        tracking=True,
        required=True)

    # ========== Attachments ==========
    document_attachment_ids = fields.Many2many(
        'ir.attachment',
        'toolbox_talk_doc_rel',
        'talk_id',
        'attachment_id',
        string='Documents'
    )

    photo_attachment_ids = fields.Many2many(
        'ir.attachment',
        'toolbox_talk_photo_rel',
        'talk_id',
        'attachment_id',
        string='Photos'
    )

    # ========== Notes ==========
    notes = fields.Text(
        string='Notes'
    )

    feedback = fields.Text(
        string='Feedback',
        help='Feedback received from attendees'
    )

    # ========== Company ==========
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # ========== Compute Fields ==========

    @api.depends('start_time', 'duration_hours')
    def _compute_times(self):
        """Compute end time from duration."""
        for record in self:
            if record.start_time and record.duration_hours:
                record.end_time = record.start_time + record.duration_hours
            else:
                record.end_time = 0.0

    @api.depends('attendee_ids')
    def _compute_attendee_count(self):
        """Compute number of attendees."""
        for record in self:
            record.attendee_count = len(record.attendee_ids)

    @api.depends('signatories')
    def _compute_signatory_count(self):
        """Compute number of signatories."""
        for record in self:
            if record.signatories:
                record.signatory_count = len(record.signatories.split('\n'))
            else:
                record.signatory_count = 0

    # ========== Action Methods ==========

    def action_start(self):
        """Start the toolbox talk."""
        self.ensure_one()

        if self.state != 'planned':
            raise ValidationError(_('Only planned toolbox talks can be started.'))

        self.write({
            'state': 'in_progress',
            'start_time': fields.Datetime.now().hour + fields.Datetime.now().minute / 60.0
        })

        self.message_post(
            body=_("""
                <b>Toolbox Talk Started</b><br/>
                Topic: %s<br/>
                Started by: %s
            """) % (
                self.name,
                self.env.user.name
            ),
            subject=_('Toolbox Talk Started')
        )

    def action_complete(self):
        """Mark toolbox talk as completed."""
        self.ensure_one()

        if self.state not in ['planned', 'in_progress']:
            raise ValidationError(_('Only planned or in-progress talks can be completed.'))

        if not self.attendee_ids:
            raise ValidationError(_('Please add at least one attendee.'))

        self.write({
            'state': 'completed',
            'end_time': fields.Datetime.now().hour + fields.Datetime.now().minute / 60.0
        })

        # Calculate duration if not set
        if not self.duration_hours and self.start_time and self.end_time:
            self.duration_hours = self.end_time - self.start_time

        self.message_post(
            body=_("""
                <b>Toolbox Talk Completed</b><br/>
                Topic: %s<br/>
                Attendees: %s<br/>
                Completed by: %s
            """) % (
                self.name,
                self.attendee_count,
                self.env.user.name
            ),
            subject=_('Toolbox Talk Completed')
        )

    def action_cancel(self):
        """Cancel the toolbox talk."""
        self.ensure_one()

        if self.state == 'completed':
            raise ValidationError(_('Completed toolbox talks cannot be cancelled.'))

        self.write({'state': 'cancelled'})

        self.message_post(
            body=_("""
                <b>Toolbox Talk Cancelled</b><br/>
                Topic: %s<br/>
                Cancelled by: %s
            """) % (
                self.name,
                self.env.user.name
            ),
            subject=_('Toolbox Talk Cancelled')
        )

    def action_add_attendees(self):
        """Open wizard to add attendees."""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Attendees'),
            'res_model': 'toolbox.talk.attendees.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_talk_id': self.id,
            }
        }

    def action_send_summary(self):
        """Send summary email to attendees."""
        self.ensure_one()

        if self.state != 'completed':
            raise ValidationError(_('Only completed toolbox talks can send summaries.'))

        if not self.attendee_ids:
            raise ValidationError(_('No attendees to send summary to.'))

        # Get attendee partners
        partners = self.attendee_ids.mapped('user_id.partner_id')
        if not partners:
            raise ValidationError(_('No valid email addresses found for attendees.'))

        # Send email
        template = self.env.ref('construction_site_log.email_template_toolbox_talk_summary', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True, raise_exception=False)
            self.message_post(
                body=_("Summary email sent to %s attendees.") % len(partners),
                subject=_('Summary Sent')
            )
        else:
            raise ValidationError(_('Email template not found.'))

    # ========== Helper Methods ==========

    def get_attendance_rate(self):
        """Calculate attendance rate."""
        self.ensure_one()
        if self.attendee_count > 0:
            return 100.0  # All attendees are counted as present
        return 0.0

    def get_attendance_list(self):
        """Get formatted list of attendees."""
        self.ensure_one()
        return ', '.join(self.attendee_ids.mapped('name'))

    # ========== Constraints ==========

    @api.constrains('duration_hours')
    def _check_duration(self):
        """Validate duration is reasonable."""
        for record in self:
            if record.duration_hours < 0:
                raise ValidationError(_('Duration cannot be negative.'))
            if record.duration_hours > 4:
                raise ValidationError(_('Duration cannot exceed 4 hours.'))

    @api.constrains('start_time', 'end_time')
    def _check_times(self):
        """Validate time range."""
        for record in self:
            if record.start_time and record.end_time:
                if record.end_time < record.start_time:
                    raise ValidationError(_('End time must be after start time.'))
                if record.start_time < 0 or record.start_time > 24:
                    raise ValidationError(_('Start time must be between 0 and 24 hours.'))
                if record.end_time < 0 or record.end_time > 24:
                    raise ValidationError(_('End time must be between 0 and 24 hours.'))

    @api.constrains('attendee_ids')
    def _check_attendees(self):
        """Validate attendees are from the same company."""
        for record in self:
            if record.attendee_ids:
                company_ids = record.attendee_ids.mapped('company_id')
                if len(company_ids) > 1:
                    raise ValidationError(_('All attendees must be from the same company.'))
