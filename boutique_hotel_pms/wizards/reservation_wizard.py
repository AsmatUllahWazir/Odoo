from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class HotelReservationWizard(models.TransientModel):
    _name = 'hotel.reservation.wizard'
    _description = 'Reservation Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string='Guest',
        required=True,
        help='Guest for the reservation'
    )
    room_ids = fields.Many2many(
        'hotel.room',
        string='Rooms',
        required=True,
        help='Rooms to book'
    )
    check_in = fields.Datetime(
        string='Check-in Date',
        required=True,
        default=lambda self: fields.Datetime.now().replace(hour=15, minute=0, second=0),
        help='Check-in date and time'
    )
    check_out = fields.Datetime(
        string='Check-out Date',
        required=True,
        default=lambda self: (fields.Datetime.now() + timedelta(days=1)).replace(hour=11, minute=0, second=0),
        help='Check-out date and time'
    )
    adults = fields.Integer(
        string='Adults',
        default=1,
        required=True,
        help='Number of adults'
    )
    children = fields.Integer(
        string='Children',
        default=0,
        help='Number of children'
    )
    source = fields.Selection([
        ('walk_in', 'Walk-in'),
        ('website', 'Website'),
        ('phone', 'Phone Call'),
        ('email', 'Email'),
        ('ota', 'OTA'),
        ('corporate', 'Corporate'),
        ('travel_agent', 'Travel Agent'),
        ('other', 'Other')
    ], string='Source', required=True, default='walk_in',
        help='Source of reservation')
    notes = fields.Text(
        string='Notes',
        help='Additional notes'
    )
    special_requests = fields.Text(
        string='Special Requests',
        help='Special requests from guest'
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        readonly=True,
        help='Total amount for the stay'
    )
    number_of_nights = fields.Integer(
        string='Nights',
        compute='_compute_nights',
        readonly=True,
        help='Number of nights'
    )

    @api.depends('room_ids', 'check_in', 'check_out')
    def _compute_total_amount(self):
        for record in self:
            if record.room_ids and record.check_in and record.check_out:
                nights = (record.check_out - record.check_in).days
                record.number_of_nights = nights if nights > 0 else 1
                total = 0
                for room in record.room_ids:
                    total += room.room_type_id.base_price * record.number_of_nights
                record.total_amount = total
            else:
                record.total_amount = 0
                record.number_of_nights = 1

    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for record in self:
            if record.check_in and record.check_out:
                nights = (record.check_out - record.check_in).days
                record.number_of_nights = nights if nights > 0 else 1
            else:
                record.number_of_nights = 1

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for record in self:
            if record.check_in and record.check_out:
                if record.check_out <= record.check_in:
                    raise ValidationError('Check-out date must be after check-in date.')

    @api.constrains('room_ids', 'check_in', 'check_out')
    def _check_room_availability(self):
        for record in self:
            overlapping = self.env['hotel.reservation'].search([
                ('state', 'in', ['confirmed', 'checked_in']),
                ('check_in', '<', record.check_out),
                ('check_out', '>', record.check_in)
            ])
            if overlapping:
                overlapping_rooms = overlapping.mapped('room_ids')
                if record.room_ids & overlapping_rooms:
                    conflicting = record.room_ids & overlapping_rooms
                    raise ValidationError(
                        f'Room(s) {", ".join(conflicting.mapped("room_number"))} '
                        'are already booked for the selected dates.'
                    )

    def action_create_reservation(self):
        """Create reservation from wizard"""
        self.ensure_one()

        reservation_vals = {
            'partner_id': self.partner_id.id,
            'room_ids': [(6, 0, self.room_ids.ids)],
            'check_in': self.check_in,
            'check_out': self.check_out,
            'adults': self.adults,
            'children': self.children,
            'source': self.source,
            'notes': self.notes,
            'special_requests': self.special_requests,
            'state': 'draft',
        }

        reservation = self.env['hotel.reservation'].create(reservation_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reservation'),
            'res_model': 'hotel.reservation',
            'view_mode': 'form',
            'res_id': reservation.id,
            'target': 'current',
        }


class HotelQuickCheckinWizard(models.TransientModel):
    _name = 'hotel.quick.checkin.wizard'
    _description = 'Quick Check-in Wizard'

    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Reservation',
        required=True,
        help='Reservation to check in'
    )
    check_in_actual = fields.Datetime(
        string='Actual Check-in Time',
        required=True,
        default=fields.Datetime.now,
        help='Actual check-in time'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes about check-in'
    )

    def action_check_in(self):
        self.ensure_one()
        self.reservation_id.check_in_actual = self.check_in_actual
        self.reservation_id.action_check_in()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reservation'),
            'res_model': 'hotel.reservation',
            'view_mode': 'form',
            'res_id': self.reservation_id.id,
            'target': 'current',
        }
    