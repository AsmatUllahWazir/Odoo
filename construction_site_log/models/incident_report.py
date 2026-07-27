# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class ConstructionIncidentReport(models.Model):
    """
    Incident report model for recording and tracking site incidents.
    """
    _name = 'construction.incident.report'
    _description = 'Construction Incident Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, name desc'

    # ========== Basic Fields ==========
    name = fields.Char(
        string='Incident Reference',
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
        help='Link to the daily log if applicable'
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

    time = fields.Float(
        string='Time',
        help='Time of incident in decimal format (e.g., 14.5 = 14:30)'
    )

    # ========== Incident Details ==========
    incident_type = fields.Selection([
        ('injury', 'Injury'),
        ('near_miss', 'Near Miss'),
        ('property_damage', 'Property Damage'),
        ('environmental', 'Environmental'),
        ('fire', 'Fire'),
        ('security', 'Security Breach'),
        ('other', 'Other')
    ], string='Incident Type',
        required=True,
        tracking=True)

    severity = fields.Selection([
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('major', 'Major'),
        ('fatal', 'Fatal')
    ], string='Severity',
        required=True,
        tracking=True)

    severity_color = fields.Integer(
        compute='_compute_severity_color',
        string='Severity Color'
    )

    location = fields.Char(
        string='Location',
        required=True,
        tracking=True,
        help='Specific location where incident occurred'
    )

    description = fields.Text(
        string='Description',
        required=True,
        tracking=True,
        help='Detailed description of the incident'
    )

    # ========== People ==========
    injured_person_ids = fields.Many2many(
        'hr.employee',
        'incident_injured_person_rel',
        string='Injured Persons'
    )

    witness_ids = fields.Many2many(
        'hr.employee',
        'incident_witness_rel',
        string='Witnesses'
    )

    responsible_person_id = fields.Many2one(
        'hr.employee',
        string='Responsible Person',
        tracking=True,
        help='Person responsible for this area/activity'
    )

    investigation_lead_id = fields.Many2one(
        'hr.employee',
        string='Investigation Lead',
        tracking=True,
        help='Person leading the investigation'
    )

    reported_by_id = fields.Many2one(
        'res.users',
        string='Reported By',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True
    )

    # ========== Investigation ==========
    root_cause = fields.Text(
        string='Root Cause',
        tracking=True,
        help='Root cause analysis of the incident'
    )

    investigation_findings = fields.Text(
        string='Investigation Findings',
        help='Detailed findings from the investigation'
    )

    immediate_actions = fields.Text(
        string='Immediate Actions Taken',
        help='Actions taken immediately after the incident'
    )

    preventive_actions = fields.Text(
        string='Preventive Actions',
        help='Actions to prevent recurrence'
    )

    # ========== Dates ==========
    investigation_start_date = fields.Datetime(
        string='Investigation Start Date',
        readonly=True,
        copy=False,
        tracking=True
    )

    resolution_date = fields.Datetime(
        string='Resolution Date',
        readonly=True,
        copy=False,
        tracking=True
    )

    closed_date = fields.Datetime(
        string='Closed Date',
        readonly=True,
        copy=False,
        tracking=True
    )

    # ========== Status ==========
    status = fields.Selection([
        ('draft', 'Draft'),
        ('under_investigation', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed')
    ], string='Status',
        default='draft',
        tracking=True,
        required=True)

    status_color = fields.Integer(
        compute='_compute_status_color',
        string='Status Color'
    )

    # ========== Regulatory ==========
    reported_to_authorities = fields.Boolean(
        string='Reported to Authorities',
        tracking=True
    )

    authority_report_number = fields.Char(
        string='Authority Report Number',
        tracking=True
    )

    regulatory_body_ids = fields.Many2many(
        'res.partner',
        'incident_regulatory_rel',
        string='Regulatory Bodies',
        domain="[('is_regulatory_body', '=', True)]"
    )

    # ========== Financial ==========
    financial_impact = fields.Monetary(
        string='Financial Impact',
        currency_field='currency_id',
        help='Estimated financial impact of the incident'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    insurance_claim_number = fields.Char(
        string='Insurance Claim Number'
    )

    # ========== Attachments ==========
    photo_attachment_ids = fields.Many2many(
        'ir.attachment',
        'incident_photo_rel',
        'incident_id',
        'attachment_id',
        string='Photos'
    )

    document_attachment_ids = fields.Many2many(
        'ir.attachment',
        'incident_doc_rel',
        'incident_id',
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

    # ========== Computed Fields ==========
    days_to_resolve = fields.Integer(
        compute='_compute_days_to_resolve',
        string='Days to Resolve',
        store=True
    )

    is_high_severity = fields.Boolean(
        compute='_compute_is_high_severity',
        string='High Severity',
        store=True
    )

    # ========== Compute Methods ==========

    @api.depends('severity')
    def _compute_severity_color(self):
        """Compute color for severity level."""
        color_map = {
            'minor': 10,  # Green
            'moderate': 9,  # Yellow
            'major': 8,  # Orange
            'fatal': 7,  # Red
        }
        for record in self:
            record.severity_color = color_map.get(record.severity, 10)

    @api.depends('status')
    def _compute_status_color(self):
        """Compute color for status."""
        color_map = {
            'draft': 6,  # Blue
            'under_investigation': 8,  # Orange
            'resolved': 9,  # Yellow
            'closed': 10,  # Green
        }
        for record in self:
            record.status_color = color_map.get(record.status, 10)

    @api.depends('create_date', 'resolution_date')
    def _compute_days_to_resolve(self):
        """Compute days taken to resolve the incident."""
        for record in self:
            if record.resolution_date and record.create_date:
                delta = record.resolution_date - record.create_date
                record.days_to_resolve = delta.days if delta else 0
            else:
                record.days_to_resolve = 0

    @api.depends('severity')
    def _compute_is_high_severity(self):
        """Check if incident is high severity."""
        for record in self:
            record.is_high_severity = record.severity in ['major', 'fatal']

    # ========== CRUD Overrides ==========

    @api.model
    def create(self, vals):
        """Override create to generate sequence number."""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'construction.incident.report') or _('New')

        # Set default investigation lead if not provided
        if not vals.get('investigation_lead_id') and vals.get('severity') in ['major', 'fatal']:
            # Find safety officer
            safety_officer = self.env['hr.employee'].search([
                ('user_id', '!=', False),
                ('user_id.has_group', '=', 'construction_site_log.group_construction_safety_officer')
            ], limit=1)
            if safety_officer:
                vals['investigation_lead_id'] = safety_officer.id

        return super().create(vals)

    def write(self, vals):
        """Override write to add validation."""
        if 'status' in vals:
            if vals['status'] == 'resolved':
                for record in self:
                    if not record.root_cause:
                        raise ValidationError(
                            _('Please provide root cause before resolving incident %s.')
                            % record.name
                        )
                    if not record.preventive_actions:
                        raise ValidationError(
                            _('Please provide preventive actions before resolving incident %s.')
                            % record.name
                        )

            if vals['status'] == 'closed':
                for record in self:
                    if record.status != 'resolved':
                        raise ValidationError(
                            _('Incident must be resolved before closing.')
                        )

        return super().write(vals)

    def unlink(self):
        """Prevent deletion of non-draft incidents."""
        for record in self:
            if record.status != 'draft':
                raise ValidationError(
                    _('You cannot delete an incident that is not in draft status.')
                )
        return super().unlink()

    # ========== Action Methods ==========

    def action_start_investigation(self):
        """Start investigation for the incident."""
        self.ensure_one()

        if self.status != 'draft':
            raise ValidationError(_('Only draft incidents can be investigated.'))

        if not self.investigation_lead_id:
            raise ValidationError(_('Please assign an investigation lead.'))

        self.write({
            'status': 'under_investigation',
            'investigation_start_date': fields.Datetime.now()
        })

        # Create activity for investigation lead
        if self.investigation_lead_id.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.investigation_lead_id.user_id.id,
                summary=_('Investigate Incident: %s') % self.name,
                note=f"""
                    <b>Incident Details:</b><br/>
                    Type: {self.incident_type}<br/>
                    Severity: {self.severity}<br/>
                    Location: {self.location}<br/>
                    Description: {self.description}<br/>
                    Please conduct thorough investigation and provide findings.
                """,
                date_deadline=fields.Date.today() + timedelta(days=7)
            )

        self.message_post(
            body=_("""
                <b>Investigation Started</b><br/>
                Incident: %s<br/>
                Investigation Lead: %s<br/>
                Started by: %s
            """) % (
                self.name,
                self.investigation_lead_id.name,
                self.env.user.name
            ),
            subject=_('Investigation Started')
        )

    def action_resolve(self):
        """Resolve the incident."""
        self.ensure_one()

        if self.status != 'under_investigation':
            raise ValidationError(_('Only incidents under investigation can be resolved.'))

        if not self.root_cause:
            raise ValidationError(_('Please provide root cause before resolving.'))

        if not self.preventive_actions:
            raise ValidationError(_('Please provide preventive actions before resolving.'))

        self.write({
            'status': 'resolved',
            'resolution_date': fields.Datetime.now()
        })

        self.message_post(
            body=_("""
                <b>Incident Resolved</b><br/>
                Incident: %s<br/>
                Resolved by: %s<br/>
                Root Cause: %s<br/>
                Preventive Actions: %s
            """) % (
                self.name,
                self.env.user.name,
                self.root_cause,
                self.preventive_actions
            ),
            subject=_('Incident Resolved')
        )

    def action_close(self):
        """Close the incident report."""
        self.ensure_one()

        if self.status != 'resolved':
            raise ValidationError(_('Incident must be resolved before closing.'))

        self.write({
            'status': 'closed',
            'closed_date': fields.Datetime.now()
        })

        self.message_post(
            body=_("""
                <b>Incident Closed</b><br/>
                Incident: %s<br/>
                Closed by: %s
            """) % (
                self.name,
                self.env.user.name
            ),
            subject=_('Incident Closed')
        )

    def action_reopen(self):
        """Reopen a closed incident."""
        self.ensure_one()

        if self.status != 'closed':
            raise ValidationError(_('Only closed incidents can be reopened.'))

        self.write({
            'status': 'under_investigation',
            'closed_date': False,
            'resolution_date': False
        })

        self.message_post(
            body=_("""
                <b>Incident Reopened</b><br/>
                Incident: %s<br/>
                Reopened by: %s
            """) % (
                self.name,
                self.env.user.name
            ),
            subject=_('Incident Reopened')
        )

    def action_create_follow_up_task(self):
        """Create a follow-up task in the project."""
        self.ensure_one()

        task_vals = {
            'name': f"Incident Follow-up: {self.name}",
            'project_id': self.project_id.id,
            'description': f"""
                <b>Incident Details:</b><br/>
                Reference: {self.name}<br/>
                Type: {self.incident_type}<br/>
                Severity: {self.severity}<br/>
                Location: {self.location}<br/>
                Description: {self.description}<br/>
                <br/>
                <b>Investigation Findings:</b><br/>
                Root Cause: {self.root_cause}<br/>
                Preventive Actions: {self.preventive_actions}<br/>
                <br/>
                <a href="#" data-oe-model="construction.incident.report" data-oe-id="{self.id}">View Incident Report</a>
            """,
            'date_deadline': fields.Date.today() + timedelta(days=14),
            'user_ids': [(4,
                          self.responsible_person_id.user_id.id)] if self.responsible_person_id and self.responsible_person_id.user_id else False,
        }

        task = self.env['project.task'].create(task_vals)

        self.message_post(
            body=_("""
                <b>Follow-up Task Created</b><br/>
                Task: <a href="#" data-oe-model="project.task" data-oe-id="%d">%s</a>
            """) % (task.id, task.name),
            subject=_('Follow-up Task Created')
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': task.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_report_to_authorities(self):
        """Mark incident as reported to authorities."""
        self.ensure_one()

        if self.status != 'under_investigation':
            raise ValidationError(_('Incident must be under investigation to report to authorities.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Report to Authorities'),
            'res_model': 'incident.authority.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_incident_id': self.id,
            }
        }

    # ========== Helper Methods ==========

    def get_severity_display(self, severity):
        """Helper to get severity display name."""
        selections = dict(self._fields['severity'].selection)
        return selections.get(severity, severity)

    def get_type_display(self, incident_type):
        """Helper to get type display name."""
        selections = dict(self._fields['incident_type'].selection)
        return selections.get(incident_type, incident_type)

    # ========== Statistics Methods ==========

    @api.model
    def get_incident_stats(self, project_id=None):
        """Get statistics about incidents."""
        domain = []
        if project_id:
            domain.append(('project_id', '=', project_id))

        total = self.search_count(domain)
        open_count = self.search_count(domain + [('status', 'in', ['draft', 'under_investigation'])])
        resolved_count = self.search_count(domain + [('status', 'in', ['resolved', 'closed'])])

        injury_count = self.search_count(domain + [('incident_type', '=', 'injury')])
        near_miss_count = self.search_count(domain + [('incident_type', '=', 'near_miss')])
        property_damage_count = self.search_count(domain + [('incident_type', '=', 'property_damage')])

        return {
            'total': total,
            'open': open_count,
            'resolved': resolved_count,
            'injury': injury_count,
            'near_miss': near_miss_count,
            'property_damage': property_damage_count,
        }

    # ========== Constraints ==========

    @api.constrains('date')
    def _check_future_date(self):
        """Prevent future dates."""
        for record in self:
            if record.date and record.date > fields.Date.today():
                raise ValidationError(_('Incident date cannot be in the future.'))

    @api.constrains('time')
    def _check_time(self):
        """Validate time format."""
        for record in self:
            if record.time and (record.time < 0 or record.time > 24):
                raise ValidationError(_('Time must be between 0 and 24 hours.'))

    @api.constrains('investigation_lead_id', 'status')
    def _check_investigation_lead(self):
        """Validate investigation lead is assigned before investigation."""
        for record in self:
            if record.status == 'under_investigation' and not record.investigation_lead_id:
                raise ValidationError(
                    _('Investigation lead must be assigned before starting investigation.')
                )

    @api.constrains('reported_to_authorities', 'authority_report_number')
    def _check_authority_report(self):
        """Validate authority report number when reported to authorities."""
        for record in self:
            if record.reported_to_authorities and not record.authority_report_number:
                raise ValidationError(
                    _('Authority report number is required when reported to authorities.')
                )

    # ========== Automated Actions ==========

    def _auto_remind(self):
        """Send reminders for unresolved incidents."""
        unresolved = self.search([
            ('status', 'in', ['draft', 'under_investigation']),
            ('date', '<', fields.Date.today() - timedelta(days=7))
        ])

        for incident in unresolved:
            if incident.investigation_lead_id and incident.investigation_lead_id.user_id:
                incident.message_post(
                    body=_("""
                        <b>Reminder: Open Incident</b><br/>
                        Incident: %s<br/>
                        Status: %s<br/>
                        Days Open: %s<br/>
                        Please review and take necessary action.
                    """) % (
                        incident.name,
                        incident.status,
                        (fields.Date.today() - incident.date).days
                    ),
                    subject=_('Incident Reminder'),
                    partner_ids=[incident.investigation_lead_id.user_id.partner_id.id]
                )

        _logger.info(f"Sent reminders for {len(unresolved)} open incidents")
