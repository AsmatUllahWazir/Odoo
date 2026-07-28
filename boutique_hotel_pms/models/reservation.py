from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
import re

_logger = logging.getLogger(__name__)


class HotelReservation(models.Model):
    _name = 'hotel.reservation'
    _description = 'Hotel Reservation'
    _order = 'check_in desc, id desc'
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
        string='Reservation Number',
        required=True,
        default='New',
        copy=False,
        help='Unique reservation identifier (auto-generated)'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    # Guest Information
    partner_id = fields.Many2one(
        'res.partner',
        string='Guest',
        required=True,
        tracking=True,
        help='The guest making this reservation'
    )
    guest_name = fields.Char(
        string='Guest Name',
        related='partner_id.name',
        store=True,
        help='Name of the guest'
    )
    guest_email = fields.Char(
        string='Guest Email',
        related='partner_id.email',
        store=True,
        help='Email address of the guest'
    )
    guest_phone = fields.Char(
        string='Guest Phone',
        related='partner_id.phone',
        store=True,
        help='Phone number of the guest'
    )
    guest_mobile = fields.Char(
        string='Guest Mobile',
        related='partner_id.mobile',
        store=True,
        help='Mobile number of the guest'
    )
    guest_ids = fields.Many2many(
        'res.partner',
        'hotel_reservation_guest_rel',
        'reservation_id',
        'guest_id',
        string='Additional Guests',
        help='Other guests accompanying the primary guest'
    )
    total_guests_count = fields.Integer(
        string='Total Guests',
        compute='_compute_total_guests_count',
        store=True,
        help='Total number of guests including primary and additional'
    )

    # Room Information
    room_ids = fields.Many2many(
        'hotel.room',
        string='Rooms',
        required=True,
        tracking=True,
        help='Rooms booked for this reservation'
    )
    room_count = fields.Integer(
        string='Room Count',
        compute='_compute_room_count',
        store=True,
        help='Number of rooms in this reservation'
    )
    room_type_ids = fields.Many2many(
        'hotel.room.type',
        string='Room Types',
        compute='_compute_room_type_ids',
        store=True,
        help='Types of rooms booked'
    )
    room_type_count = fields.Integer(
        string='Room Type Count',
        compute='_compute_room_type_ids',
        store=True,
        help='Number of different room types'
    )
    primary_room_id = fields.Many2one(
        'hotel.room',
        string='Primary Room',
        compute='_compute_primary_room',
        store=True,
        help='Primary room in the reservation'
    )
    room_preferences = fields.Text(
        string='Room Preferences',
        help='Guest preferences for room (e.g., high floor, quiet, etc.)'
    )

    # Date Information
    check_in = fields.Datetime(
        string='Check-in Date & Time',
        required=True,
        tracking=True,
        help='Date and time of arrival (default check-in time: 3:00 PM)'
    )
    check_in_date = fields.Date(
        string='Check-in Date',
        compute='_compute_check_in_date',
        store=True,
        help='Check-in date only'
    )
    check_out = fields.Datetime(
        string='Check-out Date & Time',
        required=True,
        tracking=True,
        help='Date and time of departure (default check-out time: 11:00 AM)'
    )
    check_out_date = fields.Date(
        string='Check-out Date',
        compute='_compute_check_out_date',
        store=True,
        help='Check-out date only'
    )
    number_of_nights = fields.Integer(
        string='Number of Nights',
        compute='_compute_duration',
        store=True,
        help='Total number of nights for this stay'
    )
    expected_check_in_time = fields.Char(
        string='Expected Check-in Time',
        default='15:00',
        help='Expected time of check-in'
    )
    expected_check_out_time = fields.Char(
        string='Expected Check-out Time',
        default='11:00',
        help='Expected time of check-out'
    )

    # Guest Count
    adults = fields.Integer(
        string='Adults',
        default=1,
        required=True,
        help='Number of adult guests (age 12+)'
    )
    children = fields.Integer(
        string='Children',
        default=0,
        help='Number of children (age 2-11)'
    )
    infants = fields.Integer(
        string='Infants',
        default=0,
        help='Number of infants (age 0-1)'
    )
    total_people = fields.Integer(
        string='Total People',
        compute='_compute_total_people',
        store=True,
        help='Total number of people (adults + children + infants)'
    )
    extra_bed_count = fields.Integer(
        string='Extra Beds',
        default=0,
        help='Number of extra beds requested'
    )
    baby_cot_count = fields.Integer(
        string='Baby Cots',
        default=0,
        help='Number of baby cots requested'
    )

    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show')
    ], string='Status', required=True, default='draft', tracking=True,
        help='Current state of the reservation')
    state_color = fields.Char(
        string='State Color',
        compute='_compute_state_color',
        help='Color for state display'
    )
    cancellation_reason = fields.Text(
        string='Cancellation Reason',
        help='Reason for cancellation if applicable'
    )
    cancellation_date = fields.Datetime(
        string='Cancellation Date',
        help='Date and time of cancellation'
    )

    # Source and Channel
    source = fields.Selection([
        ('walk_in', 'Walk-in'),
        ('website', 'Website'),
        ('phone', 'Phone Call'),
        ('email', 'Email'),
        ('ota', 'Online Travel Agency'),
        ('corporate', 'Corporate'),
        ('travel_agent', 'Travel Agent'),
        ('group', 'Group Booking'),
        ('other', 'Other')
    ], string='Source', required=True, default='walk_in',
        help='How the reservation was made')
    source_channel_id = fields.Many2one(
        'hotel.channel',
        string='Channel',
        help='Specific channel or OTA used'
    )
    channel_reference = fields.Char(
        string='Channel Reference',
        help='Reference number from the channel/OTA'
    )
    is_ota = fields.Boolean(
        string='OTA Booking',
        compute='_compute_is_ota',
        store=True,
        help='Whether this is an OTA booking'
    )

    # Financial
    room_charges = fields.Monetary(
        string='Room Charges',
        compute='_compute_room_charges',
        store=True,
        help='Total room charges'
    )
    extra_charges = fields.Monetary(
        string='Extra Charges',
        compute='_compute_extra_charges',
        store=True,
        help='Total extra charges'
    )
    taxes = fields.Monetary(
        string='Taxes',
        compute='_compute_taxes',
        store=True,
        help='Total taxes'
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        help='Total amount for the stay'
    )
    paid_amount = fields.Monetary(
        string='Paid Amount',
        default=0.0,
        tracking=True,
        help='Amount already paid'
    )
    balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_balance_due',
        store=True,
        help='Remaining balance'
    )
    payment_due_date = fields.Date(
        string='Payment Due Date',
        help='Date by which payment should be made'
    )
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded')
    ], string='Payment Status', default='unpaid', tracking=True,
        help='Current payment status')

    # Pricing Details
    base_price = fields.Monetary(
        string='Base Price per Night',
        compute='_compute_pricing',
        store=True,
        help='Base price per night'
    )
    total_price = fields.Monetary(
        string='Total Price',
        compute='_compute_pricing',
        store=True,
        help='Total price before taxes and extras'
    )
    discount_amount = fields.Monetary(
        string='Discount Amount',
        default=0.0,
        help='Discount amount applied'
    )
    discount_percentage = fields.Float(
        string='Discount Percentage',
        default=0.0,
        help='Discount percentage applied'
    )
    discount_reason = fields.Char(
        string='Discount Reason',
        help='Reason for discount'
    )
    tax_amount = fields.Monetary(
        string='Tax Amount',
        compute='_compute_taxes',
        store=True,
        help='Amount of taxes'
    )
    tax_percentage = fields.Float(
        string='Tax Percentage',
        default=10.0,
        help='Tax percentage to apply'
    )

    # Associated Records
    folio_id = fields.Many2one(
        'hotel.folio',
        string='Folio',
        help='Associated folio/bill'
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        help='Associated sale order if applicable'
    )
    invoice_ids = fields.One2many(
        'account.move',
        'hotel_reservation_id',
        string='Invoices',
        help='Invoices generated for this reservation'
    )
    payment_ids = fields.One2many(
        'hotel.payment',
        'reservation_id',
        string='Payments',
        help='Payments made for this reservation'
    )

    # Additional Fields
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the reservation'
    )
    special_requests = fields.Text(
        string='Special Requests',
        help='Special requests from the guest'
    )
    internal_notes = fields.Text(
        string='Internal Notes',
        help='Internal notes visible only to staff'
    )
    check_in_instructions = fields.Text(
        string='Check-in Instructions',
        help='Special instructions for check-in'
    )
    check_out_instructions = fields.Text(
        string='Check-out Instructions',
        help='Special instructions for check-out'
    )

    # Dates for Reporting
    check_in_actual = fields.Datetime(
        string='Actual Check-in Time',
        help='Actual check-in time recorded'
    )
    check_out_actual = fields.Datetime(
        string='Actual Check-out Time',
        help='Actual check-out time recorded'
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

    @api.depends('name', 'partner_id')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.partner_id:
                record.display_name = f"{record.name} - {record.partner_id.name}"
            else:
                record.display_name = record.name or ''

    @api.depends('check_in')
    def _compute_check_in_date(self):
        for record in self:
            record.check_in_date = record.check_in.date() if record.check_in else False

    @api.depends('check_out')
    def _compute_check_out_date(self):
        for record in self:
            record.check_out_date = record.check_out.date() if record.check_out else False

    @api.depends('partner_id', 'guest_ids')
    def _compute_total_guests_count(self):
        for record in self:
            record.total_guests_count = 1 + len(record.guest_ids)

    @api.depends('room_ids')
    def _compute_room_count(self):
        for record in self:
            record.room_count = len(record.room_ids)

    @api.depends('room_ids')
    def _compute_room_type_ids(self):
        for record in self:
            types = record.room_ids.mapped('room_type_id')
            record.room_type_ids = types
            record.room_type_count = len(types)

    @api.depends('room_ids')
    def _compute_primary_room(self):
        for record in self:
            record.primary_room_id = record.room_ids[:1] if record.room_ids else False

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for record in self:
            if record.check_in and record.check_out:
                duration = record.check_out - record.check_in
                record.number_of_nights = duration.days if duration.days > 0 else 1
            else:
                record.number_of_nights = 1

    @api.depends('adults', 'children', 'infants')
    def _compute_total_people(self):
        for record in self:
            record.total_people = record.adults + record.children + record.infants

    @api.depends('state')
    def _compute_state_color(self):
        state_colors = {
            'draft': 'secondary',
            'confirmed': 'warning',
            'checked_in': 'success',
            'checked_out': 'primary',
            'cancelled': 'danger',
            'no_show': 'danger'
        }
        for record in self:
            record.state_color = state_colors.get(record.state, 'secondary')

    @api.depends('source')
    def _compute_is_ota(self):
        for record in self:
            record.is_ota = record.source == 'ota'

    @api.depends('room_ids', 'number_of_nights')
    def _compute_room_charges(self):
        for record in self:
            if record.room_ids and record.number_of_nights:
                total = 0
                for room in record.room_ids:
                    base_price = room.room_type_id.base_price
                    total += base_price * record.number_of_nights
                record.room_charges = total
            else:
                record.room_charges = 0.0

    @api.depends('folio_id', 'folio_id.service_line_ids', 'folio_id.service_line_ids.total_price')
    def _compute_extra_charges(self):
        for record in self:
            if record.folio_id:
                record.extra_charges = record.folio_id.extra_charges
            else:
                record.extra_charges = 0.0

    @api.depends('room_charges', 'extra_charges', 'discount_amount')
    def _compute_total_amount(self):
        for record in self:
            subtotal = record.room_charges + record.extra_charges
            record.total_amount = subtotal - record.discount_amount

    @api.depends('total_amount', 'paid_amount')
    def _compute_balance_due(self):
        for record in self:
            record.balance_due = record.total_amount - record.paid_amount

    @api.depends('room_ids', 'number_of_nights')
    def _compute_pricing(self):
        for record in self:
            if record.room_ids and record.number_of_nights:
                total = 0
                for room in record.room_ids:
                    total += room.room_type_id.base_price * record.number_of_nights
                record.total_price = total
                record.base_price = total / len(record.room_ids) if record.room_ids else 0
            else:
                record.total_price = 0.0
                record.base_price = 0.0

    @api.depends('total_price', 'tax_percentage')
    def _compute_taxes(self):
        for record in self:
            record.tax_amount = record.total_price * (record.tax_percentage / 100)
            record.taxes = record.tax_amount

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for record in self:
            if record.check_in and record.check_out:
                if record.check_out <= record.check_in:
                    raise ValidationError('Check-out date must be after check-in date.')
                if record.check_in < fields.Datetime.now() and record.state == 'draft':
                    raise ValidationError('Check-in date cannot be in the past.')

    @api.constrains('adults', 'children', 'infants')
    def _check_guest_count(self):
        for record in self:
            if record.adults < 1:
                raise ValidationError('At least one adult is required.')
            if record.total_people > 10:
                raise ValidationError('Maximum total people allowed is 10.')

    @api.constrains('room_ids', 'check_in', 'check_out')
    def _check_room_availability(self):
        for record in self:
            if record.state not in ['draft', 'cancelled']:
                overlapping = self.search([
                    ('id', '!=', record.id),
                    ('state', 'in', ['confirmed', 'checked_in']),
                    ('check_in', '<', record.check_out),
                    ('check_out', '>', record.check_in)
                ])
                if overlapping:
                    overlapping_rooms = overlapping.mapped('room_ids')
                    if record.room_ids & overlapping_rooms:
                        conflicting_rooms = record.room_ids & overlapping_rooms
                        room_names = ', '.join(conflicting_rooms.mapped('room_number'))
                        raise ValidationError(
                            f'Room(s) {room_names} are already booked for the selected dates.'
                        )

    @api.constrains('discount_amount')
    def _check_discount(self):
        for record in self:
            if record.discount_amount < 0:
                raise ValidationError('Discount amount cannot be negative.')
            if record.discount_amount > record.total_amount:
                raise ValidationError('Discount amount cannot exceed total amount.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.reservation') or 'New'
            # Set default check-in/out times if not provided
            if not vals.get('check_in'):
                today = fields.Datetime.now()
                vals['check_in'] = today.replace(hour=15, minute=0, second=0)
            if not vals.get('check_out'):
                tomorrow = fields.Datetime.now() + timedelta(days=1)
                vals['check_out'] = tomorrow.replace(hour=11, minute=0, second=0)
        return super().create(vals_list)

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('Only draft reservations can be confirmed.')
            record.state = 'confirmed'
            record.message_post(body=_('Reservation confirmed.'))

    def action_check_in(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError('Only confirmed reservations can be checked in.')

            # Update room statuses
            for room in record.room_ids:
                room.status = 'occupied'

            # Create folio
            folio_vals = {
                'reservation_id': record.id,
                'partner_id': record.partner_id.id,
                'check_in': record.check_in,
                'check_out': record.check_out,
                'state': 'open',
                'currency_id': record.currency_id.id,
                'company_id': record.company_id.id,
            }
            record.folio_id = self.env['hotel.folio'].create(folio_vals)

            # Record actual check-in time
            record.check_in_actual = fields.Datetime.now()
            record.state = 'checked_in'
            record.message_post(body=_('Guest checked in.'))

    def action_check_out(self):
        for record in self:
            if record.state != 'checked_in':
                raise UserError('Only checked-in reservations can be checked out.')

            # Update room statuses
            for room in record.room_ids:
                room.status = 'dirty'

            # Settle folio
            if record.folio_id:
                record.folio_id.action_settle()
                # Create invoice if needed
                if record.folio_id.balance_due > 0:
                    self._create_invoice(record)

            # Record actual check-out time
            record.check_out_actual = fields.Datetime.now()
            record.state = 'checked_out'
            record.message_post(body=_('Guest checked out.'))

    def action_cancel(self):
        for record in self:
            if record.state in ['checked_in', 'checked_out']:
                raise UserError('Cannot cancel a checked-in or checked-out reservation.')
            record.state = 'cancelled'
            record.cancellation_date = fields.Datetime.now()
            if record.folio_id:
                record.folio_id.action_cancel()
            # Release rooms
            for room in record.room_ids:
                if room.status in ['reserved', 'occupied']:
                    room.status = 'available'
            record.message_post(body=_('Reservation cancelled.'))

    def action_no_show(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError('Only confirmed reservations can be marked as no-show.')
            record.state = 'no_show'
            for room in record.room_ids:
                if room.status == 'reserved':
                    room.status = 'available'
            record.message_post(body=_('Guest marked as no-show.'))

    def action_send_confirmation_email(self):
        self.ensure_one()
        template = self.env.ref('boutique_hotel_pms.email_template_reservation_confirmation', False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.message_post(body=_('Confirmation email sent to guest.'))
        return True

    def action_generate_invoice(self):
        self.ensure_one()
        if self.state not in ['checked_in', 'checked_out']:
            raise UserError('Invoices can only be generated for checked-in or checked-out reservations.')
        return self._create_invoice(self)

    def _create_invoice(self, reservation):
        """Create an invoice for the reservation"""
        if not reservation.folio_id:
            return False

        # Create invoice
        invoice_vals = {
            'partner_id': reservation.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'ref': reservation.name,
            'hotel_reservation_id': reservation.id,
            'invoice_line_ids': [],
        }

        # Add room charges
        if reservation.folio_id.room_charges > 0:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'name': f'Room Charges - {reservation.name}',
                'quantity': 1,
                'price_unit': reservation.folio_id.room_charges,
                'tax_ids': False,
            }))

        # Add service charges
        for line in reservation.folio_id.service_line_ids:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'name': line.service_id.name,
                'quantity': line.quantity,
                'price_unit': line.unit_price,
                'tax_ids': False,
            }))

        invoice = self.env['account.move'].create(invoice_vals)
        reservation.invoice_ids = [(4, invoice.id)]
        return invoice

    def action_view_folio(self):
        self.ensure_one()
        if self.folio_id:
            return {
                'name': _('Folio'),
                'type': 'ir.actions.act_window',
                'res_model': 'hotel.folio',
                'view_mode': 'form',
                'res_id': self.folio_id.id,
                'target': 'current',
            }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.payment',
            'view_mode': 'tree,form',
            'domain': [('reservation_id', '=', self.id)],
            'target': 'current',
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('hotel_reservation_id', '=', self.id)],
            'target': 'current',
        }

    @api.model
    def get_upcoming_checkins(self, days=1):
        """Get upcoming check-ins for the next X days"""
        today = fields.Datetime.now()
        end_date = today + timedelta(days=days)
        return self.search([
            ('state', '=', 'confirmed'),
            ('check_in', '>=', today),
            ('check_in', '<=', end_date)
        ]).sorted('check_in')

    @api.model
    def get_today_checkins(self):
        """Get today's check-ins"""
        today = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        tomorrow = today + timedelta(days=1)
        return self.search([
            ('state', '=', 'confirmed'),
            ('check_in', '>=', today),
            ('check_in', '<', tomorrow)
        ]).sorted('check_in')

    @api.model
    def get_today_checkouts(self):
        """Get today's check-outs"""
        today = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        tomorrow = today + timedelta(days=1)
        return self.search([
            ('state', '=', 'checked_in'),
            ('check_out', '>=', today),
            ('check_out', '<', tomorrow)
        ]).sorted('check_out')

    @api.model
    def get_occupancy_stats(self, date=None):
        """Get occupancy statistics for a given date"""
        if not date:
            date = fields.Datetime.now()

        date_start = date.replace(hour=0, minute=0, second=0)
        date_end = date.replace(hour=23, minute=59, second=59)

        reservations = self.search([
            ('state', '=', 'checked_in'),
            ('check_in', '<=', date_end),
            ('check_out', '>=', date_start)
        ])

        occupied_rooms = reservations.mapped('room_ids')
        total_rooms = self.env['hotel.room'].search_count([('active', '=', True)])

        return {
            'occupied_rooms': len(occupied_rooms),
            'total_rooms': total_rooms,
            'occupancy_rate': (len(occupied_rooms) / total_rooms * 100) if total_rooms > 0 else 0,
            'reservations': reservations,
        }


class AccountMove(models.Model):
    _inherit = 'account.move'

    hotel_reservation_id = fields.Many2many('hotel.reservation')
