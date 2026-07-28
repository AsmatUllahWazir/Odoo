from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class HotelHousekeeping(models.Model):
    _name = 'hotel.housekeeping'
    _description = 'Housekeeping Task'
    _order = 'create_date desc, priority desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    # Basic Information
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Complete display name'
    )
    name = fields.Char(
        string='Task Reference',
        required=True,
        default='New',
        copy=False,
        help='Unique task identifier (auto-generated)'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # Room Information
    room_id = fields.Many2one(
        'hotel.room',
        string='Room',
        required=True,
        help='Room to be cleaned/maintained'
    )
    room_number = fields.Char(
        string='Room Number',
        related='room_id.room_number',
        store=True,
        help='Room number'
    )
    room_type_id = fields.Many2one(
        'hotel.room.type',
        string='Room Type',
        related='room_id.room_type_id',
        store=True,
        help='Room type'
    )
    floor = fields.Char(
        string='Floor',
        related='room_id.floor',
        store=True,
        help='Floor of the room'
    )

    # Task Details
    task_type = fields.Selection([
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Maintenance'),
        ('inspection', 'Inspection'),
        ('deep_cleaning', 'Deep Cleaning'),
        ('restocking', 'Restocking'),
        ('turnover', 'Room Turnover'),
        ('other', 'Other')
    ], string='Task Type', required=True, default='cleaning',
        help='Type of housekeeping task')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('inspected', 'Inspected'),
        ('cancelled', 'Cancelled')
    ], string='Status', required=True, default='pending', tracking=True,
        help='Current status of the task')
    priority = fields.Selection([
        ('urgent', 'Urgent'),
        ('high', 'High'),
        ('normal', 'Normal'),
        ('low', 'Low')
    ], string='Priority', default='normal',
        help='Priority level of the task')
    priority_color = fields.Char(
        string='Priority Color',
        compute='_compute_priority_color',
        help='Color for priority display'
    )
    description = fields.Text(
        string='Description',
        help='Detailed description of the task'
    )
    checklist = fields.Text(
        string='Checklist',
        help='List of items to check/complete'
    )

    # Assignment
    assigned_to = fields.Many2one(
        'res.users',
        string='Assigned To',
        help='Staff member assigned to this task'
    )
    assigned_by = fields.Many2one(
        'res.users',
        string='Assigned By',
        default=lambda self: self.env.user,
        help='Who assigned this task'
    )
    assignment_date = fields.Datetime(
        string='Assignment Date',
        help='Date and time assigned'
    )

    # Scheduling
    scheduled_date = fields.Datetime(
        string='Scheduled Date',
        help='Date and time the task is scheduled for'
    )
    scheduled_duration = fields.Float(
        string='Scheduled Duration (hours)',
        help='Estimated duration in hours'
    )
    start_date = fields.Datetime(
        string='Start Date',
        help='Actual start date and time'
    )
    completed_date = fields.Datetime(
        string='Completed Date',
        help='Date and time completed'
    )
    completion_duration = fields.Float(
        string='Completion Duration (hours)',
        compute='_compute_duration',
        store=True,
        help='Actual duration taken to complete'
    )

    # Quality Control
    inspected_by = fields.Many2one(
        'res.users',
        string='Inspected By',
        help='Who inspected this task'
    )
    inspection_date = fields.Datetime(
        string='Inspection Date',
        help='Date of inspection'
    )
    quality_rating = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('poor', 'Poor')
    ], string='Quality Rating',
        help='Quality rating of the work done')
    inspection_notes = fields.Text(
        string='Inspection Notes',
        help='Notes from inspection'
    )
    requires_redo = fields.Boolean(
        string='Requires Redo',
        default=False,
        help='Whether the work needs to be redone'
    )

    # Supplies and Equipment
    supplies_used = fields.Text(
        string='Supplies Used',
        help='List of supplies and quantities used'
    )
    equipment_used = fields.Text(
        string='Equipment Used',
        help='List of equipment used'
    )
    additional_supplies_needed = fields.Text(
        string='Additional Supplies Needed',
        help='Supplies that need to be ordered'
    )

    # Additional Fields
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the task'
    )
    internal_notes = fields.Text(
        string='Internal Notes',
        help='Internal notes visible only to staff'
    )
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user
    )
    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now
    )
    last_modified_by = fields.Many2one(
        'res.users',
        string='Last Modified By',
        tracking=True
    )
    last_modified_date = fields.Datetime(
        string='Last Modified Date',
        tracking=True
    )

    @api.depends('name', 'room_id')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.room_id:
                record.display_name = f"{record.name} - {record.room_id.room_number}"
            else:
                record.display_name = record.name or ''

    @api.depends('priority')
    def _compute_priority_color(self):
        priority_colors = {
            'urgent': 'danger',
            'high': 'warning',
            'normal': 'info',
            'low': 'success'
        }
        for record in self:
            record.priority_color = priority_colors.get(record.priority, 'info')

    @api.depends('start_date', 'completed_date')
    def _compute_duration(self):
        for record in self:
            if record.start_date and record.completed_date:
                duration = record.completed_date - record.start_date
                record.completion_duration = duration.total_seconds() / 3600
            else:
                record.completion_duration = 0.0

    @api.constrains('scheduled_date')
    def _check_scheduled_date(self):
        for record in self:
            if record.scheduled_date and record.scheduled_date < fields.Datetime.now():
                if record.status == 'pending':
                    raise ValidationError('Scheduled date cannot be in the past.')

    @api.constrains('completion_duration')
    def _check_duration(self):
        for record in self:
            if record.completion_duration > 24:
                raise ValidationError('Completion duration cannot exceed 24 hours.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.housekeeping') or 'New'
        return super().create(vals_list)

    def action_assign(self):
        for record in self:
            if record.status not in ['pending']:
                raise UserError('Only pending tasks can be assigned.')
            record.status = 'assigned'
            record.assignment_date = fields.Datetime.now()
            if record.assigned_to:
                record.message_post(
                    body=_('Task assigned to %s') % record.assigned_to.name
                )

    def action_start(self):
        for record in self:
            if record.status != 'assigned':
                raise UserError('Only assigned tasks can be started.')
            record.status = 'in_progress'
            record.start_date = fields.Datetime.now()
            record.message_post(body=_('Task started.'))

    def action_pause(self):
        for record in self:
            if record.status != 'in_progress':
                raise UserError('Only in-progress tasks can be paused.')
            record.status = 'on_hold'
            record.message_post(body=_('Task paused.'))

    def action_resume(self):
        for record in self:
            if record.status != 'on_hold':
                raise UserError('Only on-hold tasks can be resumed.')
            record.status = 'in_progress'
            record.message_post(body=_('Task resumed.'))

    def action_complete(self):
        for record in self:
            if record.status not in ['in_progress', 'assigned']:
                raise UserError('Only in-progress or assigned tasks can be completed.')
            record.status = 'completed'
            record.completed_date = fields.Datetime.now()
            # Update room status
            if record.room_id:
                if record.task_type == 'cleaning':
                    record.room_id.status = 'available'
                    record.room_id.last_cleaned_date = fields.Datetime.now()
                elif record.task_type == 'maintenance':
                    record.room_id.last_maintenance_date = fields.Date.today()
            record.message_post(body=_('Task completed.'))

    def action_inspect(self):
        for record in self:
            if record.status != 'completed':
                raise UserError('Only completed tasks can be inspected.')
            record.status = 'inspected'
            record.inspected_by = self.env.user
            record.inspection_date = fields.Datetime.now()
            record.message_post(body=_('Task inspected.'))

    def action_cancel(self):
        for record in self:
            if record.status in ['completed', 'inspected']:
                raise UserError('Cannot cancel a completed or inspected task.')
            record.status = 'cancelled'
            record.message_post(body=_('Task cancelled.'))

    def action_assign_to_me(self):
        self.assigned_to = self.env.user
        self.action_assign()

    def action_view_room(self):
        self.ensure_one()
        if self.room_id:
            return {
                'name': _('Room'),
                'type': 'ir.actions.act_window',
                'res_model': 'hotel.room',
                'view_mode': 'form',
                'res_id': self.room_id.id,
                'target': 'current',
            }

    @api.model
    def get_today_tasks(self):
        """Get tasks for today"""
        today = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        tomorrow = today + timedelta(days=1)
        return self.search([
            ('status', 'in', ['pending', 'assigned', 'in_progress']),
            '|',
            ('scheduled_date', '>=', today),
            ('scheduled_date', '<', tomorrow)
        ])

    @api.model
    def get_my_tasks(self):
        """Get tasks assigned to current user"""
        return self.search([
            ('assigned_to', '=', self.env.user.id),
            ('status', 'in', ['assigned', 'in_progress'])
        ])

    @api.model
    def get_summary_stats(self):
        """Get summary statistics for housekeeping dashboard"""
        return {
            'pending': self.search_count([('status', '=', 'pending')]),
            'assigned': self.search_count([('status', '=', 'assigned')]),
            'in_progress': self.search_count([('status', '=', 'in_progress')]),
            'completed': self.search_count([('status', '=', 'completed')]),
            'overdue': self.search_count([
                ('status', 'in', ['pending', 'assigned']),
                ('scheduled_date', '<', fields.Datetime.now())
            ]),
        }
