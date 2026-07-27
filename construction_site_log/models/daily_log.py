# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class ConstructionSiteDailyLog(models.Model):
    """
    Main model for construction site daily logs.
    Records daily activities, weather, manpower, materials, and progress.
    """
    _name = 'construction.site.daily.log'
    _description = 'Construction Site Daily Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, name desc'

    # ========== Basic Fields ==========
    name = fields.Char(
        string='Log Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True,
        tracking=True,
        domain="[('allow_timesheets', '=', True)]"
    )

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today,
        tracking=True
    )

    # ========== Weather Information ==========
    weather_condition = fields.Selection([
        ('sunny', 'Sunny'),
        ('cloudy', 'Cloudy'),
        ('rainy', 'Rainy'),
        ('stormy', 'Stormy'),
        ('foggy', 'Foggy'),
        ('snowy', 'Snowy'),
        ('windy', 'Windy'),
        ('other', 'Other')
    ], string='Weather Condition',
        required=True,
        tracking=True,
        default='sunny')

    temperature = fields.Float(
        string='Temperature (°C)',
        help='Temperature in degrees Celsius',
        tracking=True,
        default=25.0
    )

    wind_speed = fields.Float(
        string='Wind Speed (km/h)',
        help='Wind speed in kilometers per hour',
        tracking=True,
        default=0.0
    )

    rainfall = fields.Float(
        string='Rainfall (mm)',
        help='Rainfall in millimeters',
        tracking=True,
        default=0.0
    )

    weather_notes = fields.Text(
        string='Weather Notes'
    )

    # ========== Site Information ==========
    site_supervisor_id = fields.Many2one(
        'hr.employee',
        string='Site Supervisor',
        required=True,
        tracking=True,
        domain="[('user_id', '!=', False)]"
    )

    project_manager_id = fields.Many2one(
        'res.users',
        string='Project Manager',
        related='project_id.user_id',
        store=True
    )

    total_workers = fields.Integer(
        string='Total Workers on Site',
        compute='_compute_total_workers',
        store=True,
        tracking=True
    )

    total_planned_hours = fields.Float(
        compute='_compute_totals',
        string='Total Planned Hours',
        store=True,
        default=0.0
    )

    total_actual_hours = fields.Float(
        compute='_compute_totals',
        string='Total Actual Hours',
        store=True,
        default=0.0
    )

    total_material_value = fields.Float(
        compute='_compute_totals',
        string='Total Material Value',
        store=True,
        default=0.0
    )

    # ========== One2many Lines ==========
    manpower_line_ids = fields.One2many(
        'construction.site.daily.log.manpower',
        'log_id',
        string='Manpower',
        tracking=True
    )

    material_line_ids = fields.One2many(
        'construction.site.daily.log.material',
        'log_id',
        string='Materials Used',
        tracking=True
    )

    progress_line_ids = fields.One2many(
        'construction.site.daily.log.progress',
        'log_id',
        string='Work Progress',
        tracking=True
    )

    # ========== Safety Relations ==========
    safety_observation_ids = fields.One2many(
        'construction.safety.observation',
        'daily_log_id',
        string='Safety Observations'
    )

    incident_report_ids = fields.One2many(
        'construction.incident.report',
        'daily_log_id',
        string='Incident Reports'
    )

    toolbox_talk_ids = fields.One2many(
        'construction.toolbox.talk',
        'daily_log_id',
        string='Toolbox Talks'
    )

    safety_checklist_execution_ids = fields.One2many(
        'construction.safety.checklist.execution',
        'daily_log_id',
        string='Safety Checklist Executions'
    )

    # ========== Attachments ==========
    photo_attachment_ids = fields.Many2many(
        'ir.attachment',
        'construction_daily_log_photo_rel',
        'log_id',
        'attachment_id',
        string='Photos',
        help='Site photos and evidence'
    )

    document_attachment_ids = fields.Many2many(
        'ir.attachment',
        'construction_daily_log_doc_rel',
        'log_id',
        'attachment_id',
        string='Documents'
    )

    # ========== Notes ==========
    notes = fields.Text(
        string='Additional Notes'
    )

    # ========== State/Status ==========
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('locked', 'Locked')
    ], string='Status',
        default='draft',
        tracking=True,
        copy=False,
        readonly=True,
        required=True)

    # ========== Dates ==========
    submitted_date = fields.Datetime(
        string='Submitted Date',
        readonly=True,
        copy=False
    )

    approval_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        copy=False
    )

    locked_date = fields.Datetime(
        string='Locked Date',
        readonly=True,
        copy=False
    )

    # ========== Integration Flags ==========
    create_timesheet = fields.Boolean(
        string='Create Timesheet Entries',
        default=True,
        help='Automatically create timesheet entries from manpower data'
    )

    create_inventory_move = fields.Boolean(
        string='Create Inventory Moves',
        default=True,
        help='Automatically create inventory moves for materials consumed'
    )

    timesheet_created = fields.Boolean(
        string='Timesheets Created',
        readonly=True,
        default=False,
        copy=False
    )

    inventory_moves_created = fields.Boolean(
        string='Inventory Moves Created',
        readonly=True,
        default=False,
        copy=False
    )

    # ========== Smart Button Counts ==========
    safety_observation_count = fields.Integer(
        compute='_compute_smart_counts',
        string='Safety Observations'
    )

    incident_report_count = fields.Integer(
        compute='_compute_smart_counts',
        string='Incident Reports'
    )

    toolbox_talk_count = fields.Integer(
        compute='_compute_smart_counts',
        string='Toolbox Talks'
    )

    checklist_count = fields.Integer(
        compute='_compute_smart_counts',
        string='Checklist Executions'
    )

    photo_count = fields.Integer(
        compute='_compute_smart_counts',
        string='Photos'
    )

    # ========== Risk Level ==========
    risk_level = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk')
    ], compute='_compute_risk_level',
        string='Overall Risk Level',
        store=True,
        default='low')

    risk_level_color = fields.Integer(
        compute='_compute_risk_level_color',
        string='Risk Level Color'
    )

    # ========== Activity Summary ==========
    activity_summary = fields.Text(
        compute='_compute_activity_summary',
        string='Activity Summary'
    )

    # ========== Company ==========
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # ========== Dashboard Computed Fields ==========
    days_since_created = fields.Integer(
        compute='_compute_days_since_created',
        string='Days Since Created',
        store=True
    )

    is_overdue = fields.Boolean(
        compute='_compute_is_overdue',
        string='Is Overdue',
        store=True
    )

    approval_days = fields.Integer(
        compute='_compute_approval_days',
        string='Days to Approve'
    )

    # ========== Compute Methods ==========

    @api.depends('manpower_line_ids.planned_hours', 'manpower_line_ids.actual_hours',
                 'material_line_ids.total_value')
    def _compute_totals(self):
        """Compute total planned hours, actual hours, and material value."""
        for record in self:
            record.total_planned_hours = sum(record.manpower_line_ids.mapped('planned_hours'))
            record.total_actual_hours = sum(record.manpower_line_ids.mapped('actual_hours'))
            record.total_material_value = sum(record.material_line_ids.mapped('total_value'))

    @api.depends('manpower_line_ids.planned_workers', 'manpower_line_ids.actual_workers')
    def _compute_total_workers(self):
        """Compute total planned and actual workers."""
        for record in self:
            planned = sum(record.manpower_line_ids.mapped('planned_workers'))
            actual = sum(record.manpower_line_ids.mapped('actual_workers'))
            record.total_workers = actual or planned

    @api.depends('safety_observation_ids', 'incident_report_ids',
                 'toolbox_talk_ids', 'safety_checklist_execution_ids',
                 'photo_attachment_ids')
    def _compute_smart_counts(self):
        """Compute counts for smart buttons."""
        for record in self:
            record.safety_observation_count = len(record.safety_observation_ids)
            record.incident_report_count = len(record.incident_report_ids)
            record.toolbox_talk_count = len(record.toolbox_talk_ids)
            record.checklist_count = len(record.safety_checklist_execution_ids)
            record.photo_count = len(record.photo_attachment_ids)

    @api.depends('safety_observation_ids.severity', 'safety_observation_ids.status',
                 'incident_report_ids.severity', 'incident_report_ids.status')
    def _compute_risk_level(self):
        """Compute overall risk level based on safety observations and incidents."""
        for record in self:
            high_risk_obs = record.safety_observation_ids.filtered(
                lambda o: o.severity in ['high', 'critical'] and o.status != 'closed'
            )
            open_incidents = record.incident_report_ids.filtered(
                lambda i: i.status in ['draft', 'under_investigation']
            )
            major_incidents = record.incident_report_ids.filtered(
                lambda i: i.severity in ['major', 'fatal'] and i.status != 'closed'
            )

            if high_risk_obs or major_incidents:
                record.risk_level = 'critical'
            elif open_incidents or high_risk_obs.filtered(lambda o: o.severity == 'high'):
                record.risk_level = 'high'
            elif record.safety_observation_ids.filtered(
                    lambda o: o.severity == 'medium' and o.status != 'closed'
            ):
                record.risk_level = 'medium'
            else:
                record.risk_level = 'low'

    @api.depends('risk_level')
    def _compute_risk_level_color(self):
        """Compute color for risk level."""
        color_map = {
            'low': 10,  # Green
            'medium': 9,  # Yellow
            'high': 8,  # Orange
            'critical': 7,  # Red
        }
        for record in self:
            record.risk_level_color = color_map.get(record.risk_level, 10)

    @api.depends('progress_line_ids.activity_description', 'progress_line_ids.percentage_complete')
    def _compute_activity_summary(self):
        """Compute a summary of activities for the report."""
        for record in self:
            activities = []
            for progress in record.progress_line_ids[:5]:
                activities.append(
                    f"{progress.activity_description[:50]} "
                    f"({progress.percentage_complete:.0f}% complete)"
                )
            record.activity_summary = '\n'.join(activities) if activities else 'No activities recorded'

    @api.depends('create_date')
    def _compute_days_since_created(self):
        """Compute days since the log was created."""
        for record in self:
            if record.create_date:
                delta = fields.Datetime.now() - record.create_date
                record.days_since_created = delta.days
            else:
                record.days_since_created = 0

    @api.depends('state', 'date')
    def _compute_is_overdue(self):
        """Check if the log is overdue for submission."""
        for record in self:
            if record.state == 'draft' and record.date:
                days_passed = (fields.Date.today() - record.date).days
                record.is_overdue = days_passed > 3
            else:
                record.is_overdue = False

    @api.depends('submitted_date', 'approval_date')
    def _compute_approval_days(self):
        """Compute days taken for approval."""
        for record in self:
            if record.submitted_date and record.approval_date:
                delta = record.approval_date - record.submitted_date
                record.approval_days = delta.days
            else:
                record.approval_days = 0

    # ========== CRUD Overrides ==========

    @api.model
    def create(self, vals):
        """Override create to generate sequence number and validate."""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'construction.site.daily.log') or _('New')

        # Ensure date is set
        if not vals.get('date'):
            vals['date'] = fields.Date.today()

        return super().create(vals)

    def write(self, vals):
        """Override write to add tracking and validation."""
        if 'state' in vals and vals['state'] == 'locked':
            # Ensure all required fields are filled before locking
            for record in self:
                if record.state != 'approved':
                    raise ValidationError(_('Only approved logs can be locked.'))
                if not record.weather_condition:
                    raise ValidationError(_('Weather condition is required before locking.'))
                if not record.manpower_line_ids:
                    raise ValidationError(_('Manpower lines are required before locking.'))
                if not record.progress_line_ids:
                    raise ValidationError(_('Progress lines are required before locking.'))

        return super().write(vals)

    def unlink(self):
        """Prevent deletion of non-draft logs."""
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_('You cannot delete a log that is not in draft state.'))
        return super().unlink()

    # ========== Action Methods ==========

    def action_submit(self):
        """Submit the daily log for approval."""
        self.ensure_one()

        # Validation
        if not self.project_id:
            raise ValidationError(_('Project is required before submission.'))
        if not self.site_supervisor_id:
            raise ValidationError(_('Site Supervisor is required before submission.'))
        if not self.weather_condition:
            raise ValidationError(_('Weather condition is required.'))
        if not self.manpower_line_ids:
            raise ValidationError(_('At least one manpower line is required.'))
        if not self.progress_line_ids:
            raise ValidationError(_('At least one progress line is required.'))

        # Calculate total workers
        total_workers = sum(self.manpower_line_ids.mapped('planned_workers'))
        if total_workers == 0:
            raise ValidationError(_('Total planned workers cannot be zero.'))

        # Update state
        self.write({
            'state': 'submitted',
            'submitted_date': fields.Datetime.now()
        })

        # Auto-create timesheets if enabled
        if self.create_timesheet and not self.timesheet_created:
            self._create_timesheet_entries()

        # Send notification to project manager
        if self.project_id.user_id:
            self.message_subscribe(partner_ids=[self.project_id.user_id.partner_id.id])
            self.message_post(
                body=_("""
                    <b>Daily Log Submitted</b><br/>
                    Log: %s<br/>
                    Project: %s<br/>
                    Date: %s<br/>
                    Submitted by: %s<br/>
                    Total Workers: %s<br/>
                    <a href="#" data-oe-model="construction.site.daily.log" data-oe-id="%s">View Log</a>
                """) % (
                    self.name,
                    self.project_id.name,
                    self.date,
                    self.env.user.name,
                    self.total_workers,
                    self.id
                ),
                subject=_('Daily Log Submitted for Approval')
            )

    def action_approve(self):
        """Approve the daily log."""
        self.ensure_one()

        if self.state != 'submitted':
            raise ValidationError(_('Only submitted logs can be approved.'))

        self.write({
            'state': 'approved',
            'approval_date': fields.Datetime.now()
        })

        # Create inventory moves if enabled
        if self.create_inventory_move and not self.inventory_moves_created:
            self._create_inventory_moves()

        self.message_post(
            body=_("""
                <b>Daily Log Approved</b><br/>
                Log: %s<br/>
                Approved by: %s<br/>
                <a href="#" data-oe-model="construction.site.daily.log" data-oe-id="%s">View Log</a>
            """) % (
                self.name,
                self.env.user.name,
                self.id
            ),
            subject=_('Daily Log Approved')
        )

    def action_lock(self):
        """Lock the approved daily log."""
        self.ensure_one()

        if self.state != 'approved':
            raise ValidationError(_('Only approved logs can be locked.'))

        self.write({
            'state': 'locked',
            'locked_date': fields.Datetime.now()
        })

        self.message_post(
            body=_("Daily log %s has been locked by %s.") % (
                self.name,
                self.env.user.name
            ),
            subject=_('Daily Log Locked')
        )

    def action_reset_to_draft(self):
        """Reset locked/approved log to draft."""
        self.ensure_one()

        if self.state == 'locked':
            raise ValidationError(_('Locked logs cannot be modified.'))

        self.write({
            'state': 'draft',
            'submitted_date': False,
            'approval_date': False,
            'timesheet_created': False,
            'inventory_moves_created': False
        })

        self.message_post(
            body=_("Daily log %s has been reset to draft by %s.") % (
                self.name,
                self.env.user.name
            ),
            subject=_('Daily Log Reset')
        )

    def action_request_changes(self):
        """Request changes on a submitted log."""
        self.ensure_one()

        if self.state != 'submitted':
            raise ValidationError(_('Only submitted logs can be sent back for changes.'))

        # Show wizard for requesting changes
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Changes'),
            'res_model': 'construction.daily.log.request.changes',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_log_id': self.id,
            }
        }

    def action_generate_report(self):
        """Generate and download PDF report."""
        self.ensure_one()

        if self.state not in ['approved', 'locked']:
            raise ValidationError(_('Only approved or locked logs can generate reports.'))

        return self.env.ref('construction_site_log.action_report_construction_daily_log').report_action(self)

    # ========== Business Logic Methods ==========

    def _create_timesheet_entries(self):
        """Create timesheet entries from manpower data."""
        self.ensure_one()

        if not self.project_id.analytic_account_id:
            _logger.warning(f"No analytic account for project {self.project_id.name}")
            return

        Timesheet = self.env['account.analytic.line']
        timesheets_created = 0

        for line in self.manpower_line_ids:
            if line.actual_hours > 0:
                # Check if timesheet already exists for this log and category
                existing = Timesheet.search([
                    ('project_id', '=', self.project_id.id),
                    ('employee_id', '=', self.site_supervisor_id.id),
                    ('date', '=', self.date),
                    ('name', 'ilike', f"Daily Log {self.name}"),
                ], limit=1)

                if not existing:
                    Timesheet.create({
                        'project_id': self.project_id.id,
                        'task_id': False,
                        'employee_id': self.site_supervisor_id.id,
                        'unit_amount': line.actual_hours,
                        'account_id': self.project_id.analytic_account_id.id,
                        'name': f"Daily Log {self.name} - {line.category}",
                        'date': self.date,
                        'company_id': self.company_id.id,
                        'user_id': self.env.user.id,
                    })
                    timesheets_created += 1

        if timesheets_created > 0:
            self.write({'timesheet_created': True})
            _logger.info(f"Created {timesheets_created} timesheet entries for log {self.name}")

    def _create_inventory_moves(self):
        """Create inventory moves for materials consumed."""
        self.ensure_one()

        if not self.material_line_ids:
            return

        consumption_location = self.env.ref('stock.stock_location_consumption', raise_if_not_found=False)
        if not consumption_location:
            _logger.warning("Consumption location not found. Inventory moves will not be created.")
            return

        StockMove = self.env['stock.move']
        moves_created = 0

        for line in self.material_line_ids:
            if line.quantity_used > 0 and line.source_location_id:
                # Check if move already exists
                existing = StockMove.search([
                    ('name', 'ilike', f"Material Consumption - {self.name}"),
                    ('product_id', '=', line.product_id.id),
                    ('state', '=', 'done'),
                ], limit=1)

                if not existing:
                    move_vals = {
                        'name': f"Material Consumption - {self.name} - {line.product_id.name}",
                        'product_id': line.product_id.id,
                        'product_uom': line.product_id.uom_id.id,
                        'product_uom_qty': line.quantity_used,
                        'location_id': line.source_location_id.id,
                        'location_dest_id': consumption_location.id,
                        'state': 'draft',
                        'company_id': self.company_id.id,
                        'date': self.date,
                        'picking_type_id': self.env.ref('stock.picking_type_internal',
                                                        raise_if_not_found=False).id if self.env.ref(
                            'stock.picking_type_internal', raise_if_not_found=False) else False,
                    }
                    move = StockMove.create(move_vals)
                    move._action_confirm()
                    move._action_assign()
                    move._action_done()
                    moves_created += 1

        if moves_created > 0:
            self.write({'inventory_moves_created': True})
            _logger.info(f"Created {moves_created} inventory moves for log {self.name}")

    # ========== Smart Button Actions ==========

    def action_view_safety_observations(self):
        """Action to view linked safety observations."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Safety Observations'),
            'res_model': 'construction.safety.observation',
            'view_mode': 'tree,form',
            'domain': [('daily_log_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_daily_log_id': self.id,
            },
        }

    def action_view_incident_reports(self):
        """Action to view linked incident reports."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Incident Reports'),
            'res_model': 'construction.incident.report',
            'view_mode': 'tree,form',
            'domain': [('daily_log_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_daily_log_id': self.id,
            },
        }

    def action_view_toolbox_talks(self):
        """Action to view linked toolbox talks."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Toolbox Talks'),
            'res_model': 'construction.toolbox.talk',
            'view_mode': 'tree,form',
            'domain': [('daily_log_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_daily_log_id': self.id,
            },
        }

    def action_view_checklists(self):
        """Action to view linked safety checklists."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Safety Checklists'),
            'res_model': 'construction.safety.checklist.execution',
            'view_mode': 'tree,form',
            'domain': [('daily_log_id', '=', self.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'default_daily_log_id': self.id,
            },
        }

    # ========== Constraints ==========

    @api.constrains('date', 'project_id')
    def _check_unique_daily_log(self):
        """Ensure only one log per project per date."""
        for record in self:
            existing = self.search([
                ('date', '=', record.date),
                ('project_id', '=', record.project_id.id),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(
                    _('A daily log already exists for this project on %s. '
                      'Only one log is allowed per project per day.')
                    % record.date
                )

    @api.constrains('state')
    def _check_required_fields(self):
        """Validate required fields based on state."""
        for record in self:
            if record.state == 'submitted':
                if not record.weather_condition:
                    raise ValidationError(_('Weather condition is required for submission.'))
                if not record.manpower_line_ids:
                    raise ValidationError(_('At least one manpower line is required for submission.'))
                if not record.progress_line_ids:
                    raise ValidationError(_('At least one progress line is required for submission.'))

    @api.constrains('temperature')
    def _check_temperature(self):
        """Validate temperature is reasonable."""
        for record in self:
            if record.temperature and (record.temperature < -50 or record.temperature > 60):
                raise ValidationError(_('Temperature must be between -50°C and 60°C.'))

    # ========== Portal Methods ==========

    def _get_portal_url(self):
        """Get portal URL for the log."""
        self.ensure_one()
        return f"/my/daily_log/{self.id}"

    def _get_report_data(self):
        """Get data for report generation."""
        self.ensure_one()
        return {
            'log': self,
            'project': self.project_id,
            'manpower': self.manpower_line_ids,
            'materials': self.material_line_ids,
            'progress': self.progress_line_ids,
            'safety_observations': self.safety_observation_ids,
            'incidents': self.incident_report_ids,
            'toolbox_talks': self.toolbox_talk_ids,
            'company': self.company_id,
            'current_user': self.env.user,
            'generated_date': fields.Datetime.now(),
        }


class ConstructionSiteDailyLogManpower(models.Model):
    """Manpower lines for daily logs."""
    _name = 'construction.site.daily.log.manpower'
    _description = 'Daily Log Manpower'
    _rec_name = 'category'
    _order = 'category'

    log_id = fields.Many2one(
        'construction.site.daily.log',
        string='Daily Log',
        required=True,
        ondelete='cascade'
    )

    category = fields.Selection([
        ('management', 'Management'),
        ('supervisor', 'Supervisor'),
        ('skilled', 'Skilled Worker'),
        ('unskilled', 'Unskilled Worker'),
        ('subcontractor', 'Subcontractor'),
        ('other', 'Other')
    ], string='Category',
        required=True,
        default='skilled')

    planned_workers = fields.Integer(
        string='Planned Workers',
        required=True,
        default=0,
        help='Number of workers planned for this category'
    )

    actual_workers = fields.Integer(
        string='Actual Workers',
        required=True,
        default=0,
        help='Number of workers actually present for this category'
    )

    planned_hours = fields.Float(
        string='Planned Hours',
        required=True,
        default=0.0,
        help='Total planned hours for this category'
    )

    actual_hours = fields.Float(
        string='Actual Hours',
        required=True,
        default=0.0,
        help='Total actual hours worked for this category'
    )

    variance_workers = fields.Integer(
        compute='_compute_variances',
        string='Variance (Workers)',
        store=True
    )

    variance_hours = fields.Float(
        compute='_compute_variances',
        string='Variance (Hours)',
        store=True
    )

    utilization_rate = fields.Float(
        compute='_compute_utilization_rate',
        string='Utilization Rate (%)',
        store=True
    )

    notes = fields.Text(
        string='Notes'
    )

    @api.depends('planned_workers', 'actual_workers', 'planned_hours', 'actual_hours')
    def _compute_variances(self):
        """Compute variances between planned and actual."""
        for record in self:
            record.variance_workers = record.actual_workers - record.planned_workers
            record.variance_hours = record.actual_hours - record.planned_hours

    @api.depends('planned_workers', 'actual_workers')
    def _compute_utilization_rate(self):
        """Compute utilization rate."""
        for record in self:
            if record.planned_workers > 0:
                record.utilization_rate = (record.actual_workers / record.planned_workers) * 100
            else:
                record.utilization_rate = 0.0

    @api.constrains('planned_workers', 'actual_workers')
    def _check_workers_positive(self):
        """Ensure worker counts are non-negative."""
        for record in self:
            if record.planned_workers < 0:
                raise ValidationError(_('Planned workers cannot be negative.'))
            if record.actual_workers < 0:
                raise ValidationError(_('Actual workers cannot be negative.'))

    @api.constrains('planned_hours', 'actual_hours')
    def _check_hours_positive(self):
        """Ensure hours are non-negative."""
        for record in self:
            if record.planned_hours < 0:
                raise ValidationError(_('Planned hours cannot be negative.'))
            if record.actual_hours < 0:
                raise ValidationError(_('Actual hours cannot be negative.'))


class ConstructionSiteDailyLogMaterial(models.Model):
    """Material lines for daily logs."""
    _name = 'construction.site.daily.log.material'
    _description = 'Daily Log Material'
    _rec_name = 'product_id'
    _order = 'product_id'

    log_id = fields.Many2one(
        'construction.site.daily.log',
        string='Daily Log',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[('type', 'in', ['product', 'consu'])]"
    )

    quantity_used = fields.Float(
        string='Quantity Used',
        required=True,
        default=1.0,
        help='Quantity of material consumed'
    )

    unit = fields.Char(
        string='Unit',
        related='product_id.uom_name',
        readonly=True
    )

    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        domain="[('usage', '=', 'internal')]",
        help='Location from which material was taken'
    )

    unit_price = fields.Float(
        string='Unit Price',
        compute='_compute_unit_price',
        store=True,
        help='Cost per unit of material'
    )

    total_value = fields.Float(
        string='Total Value',
        compute='_compute_total_value',
        store=True,
        help='Total value of material consumed'
    )

    notes = fields.Text(
        string='Notes'
    )

    @api.depends('product_id')
    def _compute_unit_price(self):
        """Get unit price from product."""
        for record in self:
            if record.product_id:
                price = record.product_id.standard_price
                # If standard price is not set, try to get from product template
                if not price and record.product_id.product_tmpl_id:
                    price = record.product_id.product_tmpl_id.standard_price
                record.unit_price = price or 0.0
            else:
                record.unit_price = 0.0

    @api.depends('quantity_used', 'unit_price')
    def _compute_total_value(self):
        """Compute total material value."""
        for record in self:
            record.total_value = record.quantity_used * record.unit_price

    @api.constrains('quantity_used')
    def _check_quantity_positive(self):
        """Ensure quantity used is positive."""
        for record in self:
            if record.quantity_used <= 0:
                raise ValidationError(_('Quantity used must be greater than zero.'))

    @api.constrains('source_location_id')
    def _check_location_usage(self):
        """Ensure source location is internal."""
        for record in self:
            if record.source_location_id and record.source_location_id.usage != 'internal':
                raise ValidationError(_('Source location must be an internal location.'))


class ConstructionSiteDailyLogProgress(models.Model):
    """Progress lines for daily logs."""
    _name = 'construction.site.daily.log.progress'
    _description = 'Daily Log Progress'
    _rec_name = 'activity_description'
    _order = 'sequence, id'

    log_id = fields.Many2one(
        'construction.site.daily.log',
        string='Daily Log',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of activities'
    )

    activity_description = fields.Text(
        string='Activity Description',
        required=True,
        help='Description of the work activity'
    )

    percentage_complete = fields.Float(
        string='Percentage Complete',
        required=True,
        default=0.0,
        help='Percentage of activity completed (0-100)'
    )

    quantity_done = fields.Float(
        string='Quantity Done',
        help='Quantity of work completed'
    )

    quantity_unit = fields.Char(
        string='Unit',
        help='Unit of measurement for quantity done'
    )

    notes = fields.Text(
        string='Notes'
    )

    # Computed status based on completion
    status = fields.Selection([
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], compute='_compute_status',
        string='Status',
        store=True)

    @api.depends('percentage_complete')
    def _compute_status(self):
        """Compute status based on percentage complete."""
        for record in self:
            if record.percentage_complete >= 100:
                record.status = 'completed'
            elif record.percentage_complete > 0:
                record.status = 'in_progress'
            else:
                record.status = 'not_started'

    @api.constrains('percentage_complete')
    def _check_percentage(self):
        """Validate percentage is between 0 and 100."""
        for record in self:
            if record.percentage_complete < 0 or record.percentage_complete > 100:
                raise ValidationError(
                    _('Percentage complete must be between 0 and 100.')
                )

    @api.constrains('quantity_done')
    def _check_quantity_positive(self):
        """Ensure quantity done is non-negative."""
        for record in self:
            if record.quantity_done is not None and record.quantity_done < 0:
                raise ValidationError(_('Quantity done cannot be negative.'))
