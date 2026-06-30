# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
# from odoo.addons.web.controllers.main import Home
from odoo.addons.portal.controllers.web import Home
import json


class SalonMainController(Home):

    @http.route('/salon/booking/data', type='json', auth='public', methods=['POST'])
    def get_booking_data(self):
        """Get booking data for online booking portal"""
        services = request.env['salon.service'].search([
            ('active', '=', True)
        ])

        staff = request.env['hr.employee'].search([
            ('salon_skill_level', '!=', False)
        ])

        chairs = request.env['salon.chair'].search([
            ('active', '=', True),
            ('state', '=', 'available')
        ])

        return {
            'services': [{'id': s.id, 'name': s.name, 'price': s.price, 'duration': s.duration} for s in services],
            'staff': [{'id': e.id, 'name': e.name, 'skill': e.salon_skill_level} for e in staff],
            'chairs': [{'id': c.id, 'name': c.name, 'code': c.code} for c in chairs],
        }

    @http.route('/salon/booking/check_availability', type='json', auth='public', methods=['POST'])
    def check_availability(self, **kwargs):
        """Check staff availability for a given time slot"""
        employee_id = kwargs.get('employee_id')
        appointment_date = kwargs.get('appointment_date')
        duration = kwargs.get('duration', 30)

        if not employee_id or not appointment_date:
            return {'available': False, 'message': 'Missing required data'}

        # Parse datetime
        try:
            from datetime import datetime
            appointment_datetime = datetime.fromisoformat(appointment_date.replace('Z', '+00:00'))
        except:
            return {'available': False, 'message': 'Invalid date format'}

        # Check for overlapping appointments
        end_datetime = appointment_datetime + timedelta(minutes=int(duration))

        overlapping = request.env['salon.appointment'].search_count([
            ('employee_id', '=', int(employee_id)),
            ('appointment_date', '<', end_datetime),
            ('end_datetime', '>', appointment_datetime),
            ('state', 'not in', ['cancelled', 'no_show'])
        ])

        if overlapping > 0:
            return {'available': False, 'message': 'Staff is already booked at this time'}

        # Check working hours (simplified)
        hour = appointment_datetime.hour
        if hour < 9 or hour > 18:
            return {'available': False, 'message': 'Outside working hours'}

        return {'available': True, 'message': 'Available'}

    @http.route('/salon/booking/create', type='json', auth='public', methods=['POST'])
    def create_booking(self, **kwargs):
        """Create a new booking from online portal"""
        try:
            customer_name = kwargs.get('customer_name')
            customer_phone = kwargs.get('customer_phone')
            customer_email = kwargs.get('customer_email')
            service_ids = kwargs.get('service_ids', [])
            employee_id = kwargs.get('employee_id')
            appointment_date = kwargs.get('appointment_date')

            if not all([customer_name, customer_phone, service_ids, employee_id, appointment_date]):
                return {'success': False, 'message': 'Missing required fields'}

            # Create or get customer
            partner = request.env['res.partner'].search([
                ('phone', '=', customer_phone)
            ], limit=1)

            if not partner:
                partner = request.env['res.partner'].create({
                    'name': customer_name,
                    'phone': customer_phone,
                    'email': customer_email,
                    'customer_rank': 1,
                })

            # Parse datetime
            from datetime import datetime
            appointment_datetime = datetime.fromisoformat(appointment_date.replace('Z', '+00:00'))

            # Create appointment
            appointment = request.env['salon.appointment'].create({
                'customer_id': partner.id,
                'employee_id': int(employee_id),
                'service_ids': [(6, 0, [int(s) for s in service_ids])],
                'appointment_date': appointment_datetime,
                'is_online_booking': True,
                'state': 'confirmed',
            })

            # Get a chair automatically (first available)
            available_chair = request.env['salon.chair'].search([
                ('state', '=', 'available')
            ], limit=1)

            if available_chair:
                appointment.chair_id = available_chair.id

            return {
                'success': True,
                'message': 'Appointment booked successfully!',
                'appointment_id': appointment.id,
                'appointment_number': appointment.name
            }

        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/salon/appointment/<int:appointment_id>/cancel', type='json', auth='public', methods=['POST'])
    def cancel_appointment(self, appointment_id, **kwargs):
        """Cancel an appointment from online portal"""
        try:
            appointment = request.env['salon.appointment'].browse(appointment_id)
            if not appointment.exists():
                return {'success': False, 'message': 'Appointment not found'}

            reason = kwargs.get('reason', 'Cancelled by customer')
            appointment.action_cancel()
            appointment.cancellation_reason = reason

            return {'success': True, 'message': 'Appointment cancelled successfully'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    @http.route('/salon/booking', type='http', auth='public', website=True)
    def booking_page(self):
        """Online booking page"""
        services = request.env['salon.service'].search([
            ('active', '=', True)
        ])

        staff = request.env['hr.employee'].search([
            ('salon_skill_level', '!=', False)
        ])

        return request.render('salon_spa_management.salon_booking_portal', {
            'services': services,
            'staff': staff,
        })
