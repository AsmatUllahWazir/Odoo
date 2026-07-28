from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'
    _order = 'room_number'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    # Basic Information
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Complete display name'
    )
    room_number = fields.Char(
        string='Room Number',
        required=True,
        tracking=True,
        help='Unique room number or identifier (e.g., 101, 201, A101)'
    )
    floor = fields.Char(
        string='Floor',
        tracking=True,
        help='Floor number or name (e.g., Ground, 1st, 2nd, Basement)'
    )
    building = fields.Char(
        string='Building/Wing',
        help='Building or wing name (e.g., Main, East Wing, Garden View)'
    )
    room_type_id = fields.Many2one(
        'hotel.room.type',
        string='Room Type',
        required=True,
        tracking=True,
        help='Type/category of the room'
    )
    description = fields.Text(
        string='Description',
        help='Additional details about the room (e.g., view, special features)'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='If unchecked, this room will be hidden'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of display'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # Status Management
    status = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('dirty', 'Dirty'),
        ('maintenance', 'Maintenance'),
        ('blocked', 'Blocked'),
        ('reserved', 'Reserved'),
        ('checkout', 'Check-out')
    ], string='Status', required=True, default='available', tracking=True,
        help='Current status of the room')
    is_available = fields.Boolean(
        string='Is Available',
        compute='_compute_is_available',
        store=True,
        help='Whether the room is available for booking (status = available)'
    )
    status_color = fields.Char(
        string='Status Color',
        compute='_compute_status_color',
        help='Color code for status'
    )
    status_icon = fields.Char(
        string='Status Icon',
        compute='_compute_status_icon',
        help='Icon for status'
    )

    # Room Features
    bed_type = fields.Selection([
        ('single', 'Single Bed'),
        ('double', 'Double Bed'),
        ('queen', 'Queen Bed'),
        ('king', 'King Bed'),
        ('twin', 'Twin Beds'),
        ('bunk', 'Bunk Beds'),
        ('sofa_bed', 'Sofa Bed')
    ], string='Bed Type', help='Type of bed(s) in the room')
    bed_count = fields.Integer(
        string='Number of Beds',
        default=1,
        help='Total number of beds in the room'
    )
    bedroom_count = fields.Integer(
        string='Number of Bedrooms',
        default=1,
        help='Number of bedrooms in suites'
    )
    bathroom_count = fields.Integer(
        string='Number of Bathrooms',
        default=1,
        help='Number of bathrooms in the room'
    )
    room_size = fields.Float(
        string='Room Size (sq ft)',
        help='Size of the room in square feet'
    )

    # Amenities (Boolean fields for quick filtering)
    has_wifi = fields.Boolean(string='Free WiFi', default=True)
    has_air_conditioning = fields.Boolean(string='Air Conditioning', default=True)
    has_heating = fields.Boolean(string='Heating', default=True)
    has_tv = fields.Boolean(string='TV', default=True)
    has_cable_tv = fields.Boolean(string='Cable/Satellite TV')
    has_telephone = fields.Boolean(string='Telephone', default=True)
    has_private_bathroom = fields.Boolean(string='Private Bathroom', default=True)
    has_hairdryer = fields.Boolean(string='Hairdryer')
    has_iron = fields.Boolean(string='Ironing Facilities')
    has_safe = fields.Boolean(string='Safety Deposit Box')
    has_minibar = fields.Boolean(string='Minibar')
    has_refrigerator = fields.Boolean(string='Refrigerator')
    has_microwave = fields.Boolean(string='Microwave')
    has_kitchen = fields.Boolean(string='Kitchen/Kitchenette')
    has_coffee_machine = fields.Boolean(string='Coffee Machine')
    has_balcony = fields.Boolean(string='Balcony')
    has_terrace = fields.Boolean(string='Terrace')
    has_garden_view = fields.Boolean(string='Garden View')
    has_city_view = fields.Boolean(string='City View')
    has_sea_view = fields.Boolean(string='Sea View')
    has_mountain_view = fields.Boolean(string='Mountain View')
    has_pool_view = fields.Boolean(string='Pool View')
    is_accessible = fields.Boolean(string='Accessible Room')
    is_smoke_free = fields.Boolean(string='Smoke Free', default=True)
    is_pet_friendly = fields.Boolean(string='Pet Friendly')
    has_extra_bed = fields.Boolean(string='Extra Bed Available')
    has_baby_cot = fields.Boolean(string='Baby Cot Available')

    amenities_ids = fields.Many2many(
        'hotel.amenity',
        string='Additional Amenities',
        help='Additional amenities not covered by boolean fields'
    )

    # Maintenance and Housekeeping
    last_maintenance_date = fields.Date(
        string='Last Maintenance Date',
        help='Date when the room was last maintained'
    )
    next_maintenance_date = fields.Date(
        string='Next Maintenance Date',
        help='Scheduled date for next maintenance'
    )
    maintenance_notes = fields.Text(
        string='Maintenance Notes',
        help='Notes about maintenance issues or history'
    )
    housekeeping_task_ids = fields.One2many(
        'hotel.housekeeping',
        'room_id',
        string='Housekeeping Tasks',
        help='Housekeeping tasks for this room'
    )
    last_cleaned_date = fields.Datetime(
        string='Last Cleaned',
        help='Date and time the room was last cleaned'
    )
    cleaning_notes = fields.Text(
        string='Cleaning Notes',
        help='Notes about cleaning requirements'
    )

    # Reservations and Occupancy
    reservation_ids = fields.Many2many(
        'hotel.reservation',
        string='Reservations',
        help='All reservations for this room'
    )
    current_reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Current Reservation',
        compute='_compute_current_reservation',
        store=True,
        help='Current active reservation'
    )
    next_reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Next Reservation',
        compute='_compute_next_reservation',
        store=True,
        help='Next upcoming reservation'
    )

    # Statistics
    total_occupancy_days = fields.Integer(
        string='Total Occupancy Days',
        compute='_compute_statistics',
        store=True,
        help='Total days the room has been occupied'
    )
    total_revenue = fields.Monetary(
        string='Total Revenue',
        compute='_compute_statistics',
        store=True,
        help='Total revenue generated by this room'
    )
    average_daily_rate = fields.Monetary(
        string='Average Daily Rate',
        compute='_compute_statistics',
        store=True,
        help='Average daily rate for this room'
    )
    occupancy_rate = fields.Float(
        string='Occupancy Rate (%)',
        compute='_compute_statistics',
        store=True,
        help='Occupancy rate for this room'
    )
    total_maintenances = fields.Integer(
        string='Total Maintenances',
        compute='_compute_statistics',
        store=True,
        help='Total number of maintenance records'
    )
    average_rating = fields.Float(
        string='Average Rating',
        compute='_compute_statistics',
        store=True,
        help='Average guest rating for this room'
    )
    total_reviews = fields.Integer(
        string='Total Reviews',
        compute='_compute_statistics',
        store=True,
        help='Total number of reviews for this room'
    )

    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    @api.depends('room_number', 'room_type_id')
    def _compute_display_name(self):
        for record in self:
            if record.room_number and record.room_type_id:
                record.display_name = f"Room {record.room_number} - {record.room_type_id.name}"
            else:
                record.display_name = record.room_number or ''

    @api.depends('status')
    def _compute_is_available(self):
        for record in self:
            record.is_available = record.status == 'available'

    @api.depends('status')
    def _compute_status_color(self):
        status_colors = {
            'available': '#28a745',
            'occupied': '#007bff',
            'dirty': '#ffc107',
            'maintenance': '#dc3545',
            'blocked': '#6c757d',
            'reserved': '#17a2b8',
            'checkout': '#fd7e14'
        }
        for record in self:
            record.status_color = status_colors.get(record.status, '#6c757d')

    @api.depends('status')
    def _compute_status_icon(self):
        status_icons = {
            'available': 'fa-check-circle',
            'occupied': 'fa-user-check',
            'dirty': 'fa-broom',
            'maintenance': 'fa-tools',
            'blocked': 'fa-ban',
            'reserved': 'fa-calendar-check',
            'checkout': 'fa-door-open'
        }
        for record in self:
            record.status_icon = status_icons.get(record.status, 'fa-question-circle')

    @api.depends('reservation_ids', 'reservation_ids.state')
    def _compute_current_reservation(self):
        for record in self:
            current = record.reservation_ids.filtered(
                lambda r: r.state in ['confirmed', 'checked_in']
            ).sorted('check_in', reverse=True)
            record.current_reservation_id = current[:1] if current else False

    @api.depends('reservation_ids', 'reservation_ids.state')
    def _compute_next_reservation(self):
        for record in self:
            future = record.reservation_ids.filtered(
                lambda r: r.state in ['draft', 'confirmed'] and r.check_in > fields.Datetime.today()
            ).sorted('check_in')
            record.next_reservation_id = future[:1] if future else False

    @api.depends('reservation_ids', 'reservation_ids.state', 'reservation_ids.number_of_nights',
                 'reservation_ids.total_amount')
    def _compute_statistics(self):
        for record in self:
            checked_out = record.reservation_ids.filtered(lambda r: r.state == 'checked_out')
            record.total_occupancy_days = sum(checked_out.mapped('number_of_nights'))
            record.total_revenue = sum(checked_out.mapped('total_amount'))

            if record.total_occupancy_days > 0:
                record.average_daily_rate = record.total_revenue / record.total_occupancy_days
            else:
                record.average_daily_rate = 0.0

            # Calculate occupancy rate over the past year
            year_ago = fields.Date.today() - timedelta(days=365)
            reservations_in_year = record.reservation_ids.filtered(
                lambda r: r.state in ['checked_in', 'checked_out'] and r.check_in >= year_ago
            )
            total_days = sum(reservations_in_year.mapped('number_of_nights'))
            record.occupancy_rate = (total_days / 365) * 100 if total_days <= 365 else 100.0

            # Maintenance count
            record.total_maintenances = len(record.housekeeping_task_ids.filtered(
                lambda t: t.task_type == 'maintenance'
            ))

            # Reviews and ratings (mock data for now)
            record.total_reviews = 0
            record.average_rating = 0.0

    @api.constrains('room_number')
    def _check_room_number_unique(self):
        for record in self:
            existing = self.search([
                ('room_number', '=', record.room_number),
                ('id', '!=', record.id),
                ('company_id', '=', record.company_id.id)
            ])
            if existing:
                raise ValidationError(f'Room number "{record.room_number}" must be unique!')

    @api.constrains('bed_count', 'bedroom_count', 'bathroom_count')
    def _check_counts(self):
        for record in self:
            if record.bed_count < 1:
                raise ValidationError('Number of beds must be at least 1.')
            if record.bedroom_count < 1:
                raise ValidationError('Number of bedrooms must be at least 1.')
            if record.bathroom_count < 1:
                raise ValidationError('Number of bathrooms must be at least 1.')

    @api.constrains('room_size')
    def _check_room_size(self):
        for record in self:
            if record.room_size and record.room_size < 100:
                raise ValidationError('Room size seems too small. Minimum size is 100 sq ft.')

    def action_set_status_available(self):
        for record in self:
            record.status = 'available'
            record.message_post(body=_('Room status set to Available'))

    def action_set_status_occupied(self):
        for record in self:
            record.status = 'occupied'
            record.message_post(body=_('Room status set to Occupied'))

    def action_set_status_dirty(self):
        for record in self:
            record.status = 'dirty'
            record.message_post(body=_('Room status set to Dirty'))

    def action_set_status_maintenance(self):
        for record in self:
            record.status = 'maintenance'
            record.message_post(body=_('Room status set to Maintenance'))

    def action_set_status_blocked(self):
        for record in self:
            record.status = 'blocked'
            record.message_post(body=_('Room status set to Blocked'))

    def action_set_status_reserved(self):
        for record in self:
            record.status = 'reserved'
            record.message_post(body=_('Room status set to Reserved'))

    def action_create_housekeeping_task(self):
        return {
            'name': _('Create Housekeeping Task'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.housekeeping',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_room_id': self.id,
                'default_status': 'dirty' if self.status == 'dirty' else 'cleaning',
                'default_assigned_to': self.env.user.id,
            }
        }

    def action_view_current_reservation(self):
        self.ensure_one()
        if self.current_reservation_id:
            return {
                'name': _('Current Reservation'),
                'type': 'ir.actions.act_window',
                'res_model': 'hotel.reservation',
                'view_mode': 'form',
                'res_id': self.current_reservation_id.id,
                'target': 'current',
            }

    def action_view_next_reservation(self):
        self.ensure_one()
        if self.next_reservation_id:
            return {
                'name': _('Next Reservation'),
                'type': 'ir.actions.act_window',
                'res_model': 'hotel.reservation',
                'view_mode': 'form',
                'res_id': self.next_reservation_id.id,
                'target': 'current',
            }

    def action_view_reservations(self):
        self.ensure_one()
        return {
            'name': _('Reservations'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reservation',
            'view_mode': 'tree,form,calendar',
            'domain': [('room_ids', 'in', self.id)],
            'target': 'current',
        }

    def action_view_housekeeping_tasks(self):
        self.ensure_one()
        return {
            'name': _('Housekeeping Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.housekeeping',
            'view_mode': 'tree,form',
            'domain': [('room_id', '=', self.id)],
            'target': 'current',
        }

    @api.model
    def _get_available_rooms(self, check_in, check_out, room_type_id=None):
        """Get available rooms for given dates"""
        domain = [('status', '=', 'available')]
        if room_type_id:
            domain.append(('room_type_id', '=', room_type_id))

        # Remove rooms that have overlapping reservations
        reserved_rooms = self.env['hotel.reservation'].search([
            ('state', 'in', ['draft', 'confirmed', 'checked_in']),
            ('check_in', '<', check_out),
            ('check_out', '>', check_in)
        ]).mapped('room_ids')

        if reserved_rooms:
            domain.append(('id', 'not in', reserved_rooms.ids))

        return self.search(domain)

    def get_occupancy_calendar(self, year, month):
        """Generate occupancy calendar for this room"""
        self.ensure_one()
        calendar_data = {}
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        for day in range((end_date - start_date).days):
            current_date = start_date + timedelta(days=day)
            is_occupied = any(
                r.check_in <= current_date.date() < r.check_out
                for r in self.reservation_ids.filtered(
                    lambda r: r.state in ['confirmed', 'checked_in']
                )
            )
            calendar_data[current_date.date()] = is_occupied

        return calendar_data

    def _get_status_color_class(self):
        """Get CSS class for status"""
        status_classes = {
            'available': 'text-success',
            'occupied': 'text-primary',
            'dirty': 'text-warning',
            'maintenance': 'text-danger',
            'blocked': 'text-secondary',
            'reserved': 'text-info',
            'checkout': 'text-warning'
        }
        return status_classes.get(self.status, '')

    @api.model
    def create(self, vals):
        room = super().create(vals)
        room.message_post(body=_('Room created with number: %s') % room.room_number)
        return room

    def write(self, vals):
        result = super().write(vals)
        if 'status' in vals:
            for record in self:
                record.message_post(body=_('Room status changed to: %s') %
                                         dict(self._fields['status'].selection).get(vals['status']))
        if 'room_number' in vals:
            for record in self:
                record.message_post(body=_('Room number changed to: %s') % vals['room_number'])
        return result
