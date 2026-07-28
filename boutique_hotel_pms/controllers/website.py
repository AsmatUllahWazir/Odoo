from odoo import http, fields
from odoo.http import request
from odoo.addons.website.controllers import main
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class HotelWebsite(http.Controller):

    @http.route('/hotel', type='http', auth='public', website=True)
    def hotel_home(self, **kwargs):
        """Hotel home page"""
        room_types = request.env['hotel.room.type'].search([
            ('active', '=', True)
        ])
        amenities = request.env['hotel.amenity'].search([
            ('active', '=', True)
        ])

        # Get featured rooms (top 3 by occupancy)
        featured_rooms = room_types.sorted('occupancy_rate', reverse=True)[:3]

        # Get today's special offers
        offers = request.env['hotel.offer'].search([
            ('active', '=', True),
            ('date_start', '<=', fields.Date.today()),
            ('date_end', '>=', fields.Date.today())
        ])

        values = {
            'room_types': room_types,
            'featured_rooms': featured_rooms,
            'amenities': amenities,
            'offers': offers,
            'main_object': request.env['hotel.config.settings'].sudo().get_values(),
        }
        return request.render('boutique_hotel_pms.website_hotel_home', values)

    @http.route('/hotel/rooms', type='http', auth='public', website=True)
    def hotel_rooms(self, **kwargs):
        """Room listing page"""
        room_types = request.env['hotel.room.type'].search([
            ('active', '=', True)
        ])

        values = {
            'room_types': room_types,
            'categories': dict(request.env['hotel.room.type']._fields['name'].selection),
        }
        return request.render('boutique_hotel_pms.website_hotel_rooms', values)

    @http.route('/hotel/room/<model("hotel.room.type"):room_type>', type='http', auth='public', website=True)
    def hotel_room_detail(self, room_type, **kwargs):
        """Room detail page"""
        # Get availability for next 30 days
        today = fields.Date.today()
        availability = []

        for i in range(30):
            date = today + timedelta(days=i)
            # Check if room type has availability on this date
            available = self._check_room_availability(room_type, date)
            availability.append({
                'date': date,
                'available': available,
                'price': self._get_daily_price(room_type, date)
            })

        # Get reviews for this room type
        reviews = request.env['hotel.review'].search([
            ('room_type_id', '=', room_type.id),
            ('published', '=', True)
        ])

        values = {
            'room_type': room_type,
            'availability': availability,
            'reviews': reviews,
            'average_rating': sum(reviews.mapped('rating')) / len(reviews) if reviews else 0,
            'total_reviews': len(reviews),
            'amenities': room_type.amenities_ids,
            'features': room_type.feature_ids,
            'images': room_type.image_ids,
        }
        return request.render('boutique_hotel_pms.website_hotel_room_detail', values)

    @http.route('/hotel/booking', type='http', auth='public', website=True, methods=['GET', 'POST'])
    def hotel_booking(self, **kwargs):
        """Booking form and processing"""
        if request.httprequest.method == 'POST':
            return self._process_booking(kwargs)

        # GET request - show booking form
        room_types = request.env['hotel.room.type'].search([
            ('active', '=', True)
        ])

        values = {
            'room_types': room_types,
            'check_in': kwargs.get('check_in', ''),
            'check_out': kwargs.get('check_out', ''),
            'adults': kwargs.get('adults', 1),
            'children': kwargs.get('children', 0),
            'room_type': kwargs.get('room_type', ''),
        }
        return request.render('boutique_hotel_pms.website_hotel_booking', values)

    def _process_booking(self, data):
        """Process booking form submission"""
        try:
            # Validate required fields
            required = ['check_in', 'check_out', 'adults', 'room_type', 'guest_name', 'guest_email']
            for field in required:
                if not data.get(field):
                    return request.render('boutique_hotel_pms.website_hotel_booking_error', {
                        'error': f'Missing required field: {field}'
                    })

            # Parse dates
            check_in = datetime.strptime(data['check_in'], '%Y-%m-%d')
            check_out = datetime.strptime(data['check_out'], '%Y-%m-%d')
            adults = int(data['adults'])
            children = int(data.get('children', 0))

            # Get room type
            room_type = request.env['hotel.room.type'].browse(int(data['room_type']))
            if not room_type:
                return request.render('boutique_hotel_pms.website_hotel_booking_error', {
                    'error': 'Invalid room type selected'
                })

            # Check availability
            available_rooms = self._get_available_rooms(room_type, check_in, check_out)
            if not available_rooms:
                return request.render('boutique_hotel_pms.website_hotel_booking_error', {
                    'error': 'No rooms available for selected dates'
                })

            # Create or get guest
            guest = self._get_or_create_guest(data)

            # Create reservation
            reservation_vals = {
                'partner_id': guest.id,
                'room_ids': [(6, 0, available_rooms[:1].ids)],
                'check_in': check_in,
                'check_out': check_out,
                'adults': adults,
                'children': children,
                'source': 'website',
                'state': 'draft',
                'notes': data.get('notes', ''),
                'special_requests': data.get('special_requests', ''),
            }
            reservation = request.env['hotel.reservation'].create(reservation_vals)

            # Send confirmation email
            reservation.action_send_confirmation_email()

            return request.render('boutique_hotel_pms.website_hotel_booking_success', {
                'reservation': reservation,
            })

        except Exception as e:
            _logger.error(f'Booking error: {str(e)}')
            return request.render('boutique_hotel_pms.website_hotel_booking_error', {
                'error': 'An error occurred while processing your booking. Please try again.'
            })

    @http.route('/hotel/availability', type='json', auth='public', methods=['POST'])
    def check_availability(self, **kwargs):
        """Check room availability via AJAX"""
        try:
            data = json.loads(request.httprequest.data)
            room_type_id = data.get('room_type_id')
            check_in = datetime.strptime(data.get('check_in'), '%Y-%m-%d')
            check_out = datetime.strptime(data.get('check_out'), '%Y-%m-%d')

            if not room_type_id:
                return {'error': 'Room type is required'}

            room_type = request.env['hotel.room.type'].browse(int(room_type_id))
            if not room_type:
                return {'error': 'Invalid room type'}

            available_rooms = self._get_available_rooms(room_type, check_in, check_out)

            return {
                'available': len(available_rooms) > 0,
                'available_count': len(available_rooms),
                'rooms': [{'id': r.id, 'number': r.room_number} for r in available_rooms],
                'price': self._calculate_total_price(room_type, check_in, check_out),
            }
        except Exception as e:
            return {'error': str(e)}

    @http.route('/hotel/rates', type='json', auth='public', methods=['POST'])
    def get_rates(self, **kwargs):
        """Get room rates via AJAX"""
        try:
            data = json.loads(request.httprequest.data)
            room_type_id = data.get('room_type_id')
            check_in = datetime.strptime(data.get('check_in'), '%Y-%m-%d')
            check_out = datetime.strptime(data.get('check_out'), '%Y-%m-%d')

            room_type = request.env['hotel.room.type'].browse(int(room_type_id))
            if not room_type:
                return {'error': 'Invalid room type'}

            total_price = self._calculate_total_price(room_type, check_in, check_out)
            nights = (check_out - check_in).days

            return {
                'price_per_night': room_type.base_price,
                'total_price': total_price,
                'nights': nights,
                'breakdown': self._get_price_breakdown(room_type, check_in, check_out),
            }
        except Exception as e:
            return {'error': str(e)}

    def _check_room_availability(self, room_type, date):
        """Check if room type has availability on a specific date"""
        rooms = request.env['hotel.room'].search([
            ('room_type_id', '=', room_type.id),
            ('status', '=', 'available')
        ])

        # Check if rooms are already booked for this date
        date_start = date.replace(hour=0, minute=0, second=0)
        date_end = date.replace(hour=23, minute=59, second=59)

        reserved_rooms = request.env['hotel.reservation'].search([
            ('state', 'in', ['confirmed', 'checked_in']),
            ('check_in', '<=', date_end),
            ('check_out', '>=', date_start)
        ]).mapped('room_ids')

        available = rooms - reserved_rooms
        return len(available) > 0

    def _get_available_rooms(self, room_type, check_in, check_out):
        """Get available rooms for given dates"""
        rooms = request.env['hotel.room'].search([
            ('room_type_id', '=', room_type.id),
            ('status', '=', 'available')
        ])

        # Check for overlapping reservations
        reserved_rooms = request.env['hotel.reservation'].search([
            ('state', 'in', ['confirmed', 'checked_in']),
            ('check_in', '<', check_out),
            ('check_out', '>', check_in)
        ]).mapped('room_ids')

        return rooms - reserved_rooms

    def _get_daily_price(self, room_type, date):
        """Get price for a specific date"""
        # Check if date is weekend
        is_weekend = date.weekday() in [4, 5]  # Friday and Saturday

        if is_weekend and room_type.weekend_price:
            return room_type.weekend_price
        else:
            return room_type.base_price

    def _calculate_total_price(self, room_type, check_in, check_out):
        """Calculate total price for a stay"""
        total = 0
        current_date = check_in
        while current_date < check_out:
            total += self._get_daily_price(room_type, current_date)
            current_date += timedelta(days=1)
        return total

    def _get_price_breakdown(self, room_type, check_in, check_out):
        """Get detailed price breakdown"""
        breakdown = []
        current_date = check_in
        while current_date < check_out:
            breakdown.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'price': self._get_daily_price(room_type, current_date)
            })
            current_date += timedelta(days=1)
        return breakdown

    def _get_or_create_guest(self, data):
        """Get existing guest or create new one"""
        Partner = request.env['res.partner']

        # Check if guest exists by email
        guest = Partner.search([('email', '=', data['guest_email'])], limit=1)

        if not guest:
            # Create new partner
            guest_vals = {
                'name': data['guest_name'],
                'email': data['guest_email'],
                'phone': data.get('guest_phone', ''),
                'mobile': data.get('guest_mobile', ''),
                'street': data.get('guest_address', ''),
                'city': data.get('guest_city', ''),
                'country_id': int(data['guest_country']) if data.get('guest_country') else False,
                'is_company': False,
            }
            guest = Partner.create(guest_vals)

            # Create hotel guest record
            request.env['hotel.guest'].create({
                'partner_id': guest.id,
                'preferences': data.get('preferences', ''),
                'special_diet': data.get('dietary_requirements', ''),
            })

        return guest
