from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class HotelRoomChangeWizard(models.TransientModel):
    _name = 'hotel.room.change.wizard'
    _description = 'Room Change Wizard'

    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Reservation',
        required=True,
        help='Reservation to change room'
    )
    current_room_ids = fields.Many2many(
        'hotel.room',
        string='Current Rooms',
        compute='_compute_current_rooms',
        readonly=True,
        help='Currently assigned rooms'
    )
    new_room_ids = fields.Many2many(
        'hotel.room',
        string='New Rooms',
        required=True,
        help='New rooms to assign'
    )
    reason = fields.Text(
        string='Reason',
        required=True,
        help='Reason for room change'
    )

    @api.depends('reservation_id')
    def _compute_current_rooms(self):
        for record in self:
            if record.reservation_id:
                record.current_room_ids = record.reservation_id.room_ids
            else:
                record.current_room_ids = False

    @api.constrains('new_room_ids', 'reservation_id')
    def _check_room_availability(self):
        for record in self:
            if record.new_room_ids and record.reservation_id:
                # Check if new rooms are available for the reservation dates
                overlapping = self.env['hotel.reservation'].search([
                    ('id', '!=', record.reservation_id.id),
                    ('state', 'in', ['confirmed', 'checked_in']),
                    ('check_in', '<', record.reservation_id.check_out),
                    ('check_out', '>', record.reservation_id.check_in)
                ])
                if overlapping:
                    overlapping_rooms = overlapping.mapped('room_ids')
                    if record.new_room_ids & overlapping_rooms:
                        conflicting = record.new_room_ids & overlapping_rooms
                        raise ValidationError(
                            f'Room(s) {", ".join(conflicting.mapped("room_number"))} '
                            'are not available for the selected dates.'
                        )

    def action_change_room(self):
        self.ensure_one()

        # Update reservation rooms
        self.reservation_id.room_ids = self.new_room_ids

        # Update room statuses
        for room in self.current_room_ids:
            if room.status == 'reserved':
                room.status = 'available'

        for room in self.new_room_ids:
            if self.reservation_id.state == 'confirmed':
                room.status = 'reserved'
            elif self.reservation_id.state == 'checked_in':
                room.status = 'occupied'

        # Log the change
        self.reservation_id.message_post(
            body=_('Room changed from %s to %s. Reason: %s') % (
                ', '.join(self.current_room_ids.mapped('room_number')),
                ', '.join(self.new_room_ids.mapped('room_number')),
                self.reason
            )
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reservation'),
            'res_model': 'hotel.reservation',
            'view_mode': 'form',
            'res_id': self.reservation_id.id,
            'target': 'current',
        }
    