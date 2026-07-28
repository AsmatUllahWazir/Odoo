from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
import json
import base64
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class HotelAPI(http.Controller):

    @http.route('/api/hotel/rooms', type='json', auth='public', methods=['GET'])
    def api_rooms(self, **kwargs):
        """Get all rooms with availability"""
        try:
            rooms = request.env['hotel.room'].search([
                ('active', '=', True)
            ])

            room_data = []
            for room in rooms:
                room_data.append({
                    'id': room.id,
                    'number': room.room_number,
                    'floor': room.floor,
                    'type': room.room_type_id.name,
                    'type_code': room.room_type_id.code,
                    'status': room.status,
                    'capacity': room.room_type_id.capacity,
                    'price': room.room_type_id.base_price,
                    'amenities': [a.name for a in room.amenities_ids],
                    'is_available': room.is_available,
                })

            return {
                'status': 'success',
                'data': room_data,
                'total': len(room_data)
            }
        except Exception as e:
            _logger.error(f'API Error: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/api/hotel/availability', type='json', auth='public', methods=['POST'])
    def api_check_availability(self, **kwargs):
        """Check room availability for dates"""
        try:
            data = json.loads(request.httprequest.data)
            check_in = datetime.strptime(data['check_in'], '%Y-%m-%d')
            check_out = datetime.strptime(data['check_out'], '%Y-%m-%d')
            room_type_id = data.get('room_type_id')

            if not check_in or not check_out:
                return {
                    'status': 'error',
                    'message': 'Check-in and check-out dates are required'
                }

            domain = [('active', '=', True)]
            if room_type_id:
                domain.append(('room_type_id', '=', int(room_type_id)))

            available_rooms = request.env['hotel.room']._get_available_rooms(
                check_in, check_out, room_type_id
            )

            room_data = []
            for room in available_rooms:
                room_data.append({
                    'id': room.id,
                    'number': room.room_number,
                    'floor': room.floor,
                    'type': room.room_type_id.name,
                    'price': room.room_type_id.base_price,
                    'capacity': room.room_type_id.capacity,
                })

            return {
                'status': 'success',
                'data': {
                    'available_rooms': len(room_data),
                    'rooms': room_data,
                    'check_in': data['check_in'],
                    'check_out': data['check_out'],
                }
            }
        except Exception as e:
            _logger.error(f'API Error: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/api/hotel/reservation', type='json', auth='public', methods=['POST'])
    def api_create_reservation(self, **kwargs):
        """Create a reservation via API"""
        try:
            data = json.loads(request.httprequest.data)

            # Validate required fields
            required = ['partner_id', 'room_ids', 'check_in', 'check_out', 'adults']
            for field in required:
                if not data.get(field):
                    return {
                        'status': 'error',
                        'message': f'Missing required field: {field}'
                    }

            # Parse dates
            check_in = datetime.strptime(data['check_in'], '%Y-%m-%d')
            check_out = datetime.strptime(data['check_out'], '%Y-%m-%d')

            # Create reservation
            reservation_vals = {
                'partner_id': int(data['partner_id']),
                'room_ids': [(6, 0, [int(r) for r in data['room_ids']])],
                'check_in': check_in,
                'check_out': check_out,
                'adults': int(data['adults']),
                'children': int(data.get('children', 0)),
                'source': data.get('source', 'other'),
                'notes': data.get('notes', ''),
                'state': 'draft',
            }

            reservation = request.env['hotel.reservation'].create(reservation_vals)

            return {
                'status': 'success',
                'data': {
                    'id': reservation.id,
                    'name': reservation.name,
                    'guest': reservation.partner_id.name,
                    'check_in': str(reservation.check_in),
                    'check_out': str(reservation.check_out),
                    'total_amount': reservation.total_amount,
                    'state': reservation.state,
                }
            }
        except Exception as e:
            _logger.error(f'API Error: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/api/hotel/reservation/<int:reservation_id>', type='json', auth='public', methods=['GET'])
    def api_get_reservation(self, reservation_id, **kwargs):
        """Get reservation details"""
        try:
            reservation = request.env['hotel.reservation'].browse(reservation_id)
            if not reservation:
                return {
                    'status': 'error',
                    'message': 'Reservation not found'
                }

            return {
                'status': 'success',
                'data': {
                    'id': reservation.id,
                    'name': reservation.name,
                    'guest': {
                        'id': reservation.partner_id.id,
                        'name': reservation.partner_id.name,
                        'email': reservation.partner_id.email,
                        'phone': reservation.partner_id.phone,
                    },
                    'rooms': [{
                        'id': r.id,
                        'number': r.room_number,
                        'type': r.room_type_id.name,
                    } for r in reservation.room_ids],
                    'check_in': str(reservation.check_in),
                    'check_out': str(reservation.check_out),
                    'nights': reservation.number_of_nights,
                    'adults': reservation.adults,
                    'children': reservation.children,
                    'total_amount': reservation.total_amount,
                    'paid_amount': reservation.paid_amount,
                    'balance_due': reservation.balance_due,
                    'state': reservation.state,
                    'source': reservation.source,
                    'notes': reservation.notes,
                }
            }
        except Exception as e:
            _logger.error(f'API Error: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/api/hotel/reservation/<int:reservation_id>/state', type='json', auth='public', methods=['POST'])
    def api_update_reservation_state(self, reservation_id, **kwargs):
        """Update reservation state"""
        try:
            data = json.loads(request.httprequest.data)
            new_state = data.get('state')

            if not new_state:
                return {
                    'status': 'error',
                    'message': 'State is required'
                }

            reservation = request.env['hotel.reservation'].browse(reservation_id)
            if not reservation:
                return {
                    'status': 'error',
                    'message': 'Reservation not found'
                }

            if new_state == 'confirm':
                reservation.action_confirm()
            elif new_state == 'checkin':
                reservation.action_check_in()
            elif new_state == 'checkout':
                reservation.action_check_out()
            elif new_state == 'cancel':
                reservation.action_cancel()
            else:
                return {
                    'status': 'error',
                    'message': f'Invalid state: {new_state}'
                }

            return {
                'status': 'success',
                'data': {
                    'id': reservation.id,
                    'state': reservation.state,
                    'message': f'Reservation state updated to {reservation.state}'
                }
            }
        except Exception as e:
            _logger.error(f'API Error: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/api/hotel/guest/<int:guest_id>', type='json', auth='public', methods=['GET'])
    def api_get_guest(self, guest_id, **kwargs):
        """Get guest details"""
        try:
            guest = request.env['hotel.guest'].search([('partner_id', '=', guest_id)], limit=1)
            if not guest:
                return {
                    'status': 'error',
                    'message': 'Guest not found'
                }

            return {
                'status': 'success',
                'data': {
                    'id': guest.partner_id.id,
                    'name': guest.partner_id.name,
                    'email': guest.partner_id.email,
                    'phone': guest.partner_id.phone,
                    'mobile': guest.partner_id.mobile,
                    'preferences': guest.preferences,
                    'total_stays': guest.total_stays,
                    'total_spent': guest.total_spent,
                    'last_visit': str(guest.last_visit) if guest.last_visit else None,
                    'is_vip': guest.is_vip,
                    'is_blacklisted': guest.is_blacklisted,
                }
            }
        except Exception as e:
            _logger.error(f'API Error: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/api/hotel/dashboard', type='json', auth='public', methods=['GET'])
    def api_dashboard(self, **kwargs):
        """Get dashboard data"""
        try:
            dashboard = request.env['hotel.dashboard'].sudo()
            data = dashboard.get_dashboard_data()

            return {
                'status': 'success',
                'data': data
            }
        except Exception as e:
            _logger.error(f'API Error: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }

    @http.route('/api/hotel/occupancy/forecast', type='json', auth='public', methods=['GET'])
    def api_occupancy_forecast(self, **kwargs):
        """Get occupancy forecast"""
        try:
            days = int(kwargs.get('days', 30))
            dashboard = request.env['hotel.dashboard'].sudo()
            forecast = dashboard.get_occupancy_forecast(days)

            return {
                'status': 'success',
                'data': forecast
            }
        except Exception as e:
            _logger.error(f'API Error: {str(e)}')
            return {
                'status': 'error',
                'message': str(e)
            }
        