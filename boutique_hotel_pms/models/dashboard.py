from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import logging

_logger = logging.getLogger(__name__)


class HotelDashboard(models.Model):
    _name = 'hotel.dashboard'
    _description = 'Hotel Dashboard'
    _auto = False
    _rec_name = 'id'

    # This is a virtual model for dashboard data
    id = fields.Integer(string='ID', readonly=True)
    date = fields.Date(string='Date', readonly=True)

    # Key Metrics
    total_reservations = fields.Integer(string='Total Reservations', readonly=True)
    confirmed_reservations = fields.Integer(string='Confirmed Reservations', readonly=True)
    checked_in = fields.Integer(string='Checked In', readonly=True)
    checked_out = fields.Integer(string='Checked Out', readonly=True)
    cancelled = fields.Integer(string='Cancelled', readonly=True)

    total_rooms = fields.Integer(string='Total Rooms', readonly=True)
    available_rooms = fields.Integer(string='Available Rooms', readonly=True)
    occupied_rooms = fields.Integer(string='Occupied Rooms', readonly=True)
    dirty_rooms = fields.Integer(string='Dirty Rooms', readonly=True)
    maintenance_rooms = fields.Integer(string='Maintenance Rooms', readonly=True)

    total_revenue = fields.Float(string='Total Revenue', readonly=True)
    average_daily_rate = fields.Float(string='Average Daily Rate', readonly=True)
    revenue_per_available_room = fields.Float(string='RevPAR', readonly=True)
    occupancy_rate = fields.Float(string='Occupancy Rate (%)', readonly=True)

    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        """Initialize the dashboard view"""
        pass

    @api.model
    def get_dashboard_data(self):
        """Get comprehensive dashboard data"""
        today = fields.Date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Room Statistics
        rooms = self.env['hotel.room'].search([('active', '=', True)])
        total_rooms = len(rooms)
        available_rooms = len(rooms.filtered(lambda r: r.status == 'available'))
        occupied_rooms = len(rooms.filtered(lambda r: r.status == 'occupied'))
        dirty_rooms = len(rooms.filtered(lambda r: r.status == 'dirty'))
        maintenance_rooms = len(rooms.filtered(lambda r: r.status == 'maintenance'))

        # Reservation Statistics
        all_reservations = self.env['hotel.reservation'].search([])
        total_reservations = len(all_reservations)
        confirmed = len(all_reservations.filtered(lambda r: r.state == 'confirmed'))
        checked_in = len(all_reservations.filtered(lambda r: r.state == 'checked_in'))
        checked_out = len(all_reservations.filtered(lambda r: r.state == 'checked_out'))
        cancelled = len(all_reservations.filtered(lambda r: r.state == 'cancelled'))

        # Revenue Statistics
        invoices = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('move_type', '=', 'out_invoice'),
            ('invoice_date', '>=', month_ago)
        ])
        total_revenue = sum(invoices.mapped('amount_total'))

        # Today's check-ins and check-outs
        today_checkins = self.env['hotel.reservation'].get_today_checkins()
        today_checkouts = self.env['hotel.reservation'].get_today_checkouts()

        # Housekeeping Statistics
        housekeeping = self.env['hotel.housekeeping']
        pending_tasks = housekeeping.search_count([('status', '=', 'pending')])
        in_progress_tasks = housekeeping.search_count([('status', '=', 'in_progress')])

        # Guest Statistics
        guests = self.env['hotel.guest'].search([])
        total_guests = len(guests)
        vip_guests = len(guests.filtered(lambda g: g.is_vip))
        blacklisted = len(guests.filtered(lambda g: g.is_blacklisted))

        # Occupancy Rate
        occupancy_rate = (occupied_rooms / total_rooms * 100) if total_rooms > 0 else 0

        # ADR and RevPAR
        today_revenue = sum(self.env['hotel.reservation'].search([
            ('check_in', '<=', today),
            ('check_out', '>', today),
            ('state', '=', 'checked_in')
        ]).mapped('total_amount'))

        average_daily_rate = today_revenue / occupied_rooms if occupied_rooms > 0 else 0
        revenue_per_available_room = today_revenue / total_rooms if total_rooms > 0 else 0

        # Upcoming Arrivals
        upcoming_arrivals = self.env['hotel.reservation'].search([
            ('state', '=', 'confirmed'),
            ('check_in', '>=', today),
            ('check_in', '<=', today + timedelta(days=7))
        ]).sorted('check_in')

        # Departures
        upcoming_departures = self.env['hotel.reservation'].search([
            ('state', '=', 'checked_in'),
            ('check_out', '>=', today),
            ('check_out', '<=', today + timedelta(days=7))
        ]).sorted('check_out')

        # Revenue by Room Type
        revenue_by_type = {}
        for room in rooms:
            if room.room_type_id.name not in revenue_by_type:
                revenue_by_type[room.room_type_id.name] = 0
            revenue_by_type[room.room_type_id.name] += room.total_revenue or 0

        # Monthly Trends
        monthly_data = []
        for i in range(6):
            month_date = today - relativedelta(months=i)
            start_date = month_date.replace(day=1)
            end_date = (start_date + relativedelta(months=1)) - timedelta(days=1)

            month_reservations = self.env['hotel.reservation'].search([
                ('check_in', '>=', start_date),
                ('check_in', '<=', end_date),
                ('state', 'in', ['checked_in', 'checked_out'])
            ])

            monthly_data.append({
                'month': month_date.strftime('%b %Y'),
                'reservations': len(month_reservations),
                'revenue': sum(month_reservations.mapped('total_amount')),
                'occupancy': (len(month_reservations) / total_rooms * 100) if total_rooms > 0 else 0
            })

        # Recent Activity
        recent_reservations = self.env['hotel.reservation'].search([], limit=10, order='create_date desc')

        return {
            'room_stats': {
                'total': total_rooms,
                'available': available_rooms,
                'occupied': occupied_rooms,
                'dirty': dirty_rooms,
                'maintenance': maintenance_rooms,
                'occupancy_rate': occupancy_rate,
            },
            'reservation_stats': {
                'total': total_reservations,
                'confirmed': confirmed,
                'checked_in': checked_in,
                'checked_out': checked_out,
                'cancelled': cancelled,
            },
            'revenue_stats': {
                'total': total_revenue,
                'today': today_revenue,
                'adr': average_daily_rate,
                'revpar': revenue_per_available_room,
            },
            'today_activity': {
                'checkins': len(today_checkins),
                'checkouts': len(today_checkouts),
                'housekeeping_pending': pending_tasks,
                'housekeeping_progress': in_progress_tasks,
            },
            'guest_stats': {
                'total': total_guests,
                'vip': vip_guests,
                'blacklisted': blacklisted,
            },
            'upcoming': {
                'arrivals': upcoming_arrivals[:5],
                'departures': upcoming_departures[:5],
            },
            'revenue_by_type': revenue_by_type,
            'monthly_trends': monthly_data,
            'recent_activity': recent_reservations,
        }

    @api.model
    def get_occupancy_forecast(self, days=30):
        """Get occupancy forecast for the next N days"""
        today = fields.Date.today()
        forecast = []

        for i in range(days):
            current_date = today + timedelta(days=i)

            # Get reservations for this date
            reservations = self.env['hotel.reservation'].search([
                ('check_in', '<=', current_date),
                ('check_out', '>', current_date),
                ('state', 'in', ['confirmed', 'checked_in'])
            ])

            occupied = len(reservations.mapped('room_ids'))
            total = self.env['hotel.room'].search_count([('active', '=', True)])

            forecast.append({
                'date': current_date,
                'occupied': occupied,
                'total': total,
                'occupancy_rate': (occupied / total * 100) if total > 0 else 0,
            })

        return forecast
    