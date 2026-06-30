# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class SalonDashboard(models.TransientModel):
    _name = 'salon.dashboard'
    _description = 'Salon Dashboard'

    # Today's Statistics
    today_appointments = fields.Integer(string="Today's Appointments", compute='_compute_dashboard_data')
    today_completed = fields.Integer(string="Completed Today", compute='_compute_dashboard_data')
    today_revenue = fields.Monetary(string="Today's Revenue", compute='_compute_dashboard_data')
    today_orders = fields.Integer(string="Today's Orders", compute='_compute_dashboard_data')

    # Staff Statistics
    active_staff = fields.Integer(string="Active Staff", compute='_compute_dashboard_data')
    staff_on_break = fields.Integer(string="Staff on Break", compute='_compute_dashboard_data')

    # Chair Statistics
    available_chairs = fields.Integer(string="Available Chairs", compute='_compute_dashboard_data')
    occupied_chairs = fields.Integer(string="Occupied Chairs", compute='_compute_dashboard_data')

    # Revenue Statistics
    weekly_revenue = fields.Monetary(string="Weekly Revenue", compute='_compute_dashboard_data')
    monthly_revenue = fields.Monetary(string="Monthly Revenue", compute='_compute_dashboard_data')

    # Recent Appointments
    recent_appointment_ids = fields.One2many('salon.appointment', string='Recent Appointments',
                                             compute='_compute_dashboard_data')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.depends()
    def _compute_dashboard_data(self):
        today = fields.Date.today()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)

        # Get current time for staff status
        now = datetime.now()

        for dashboard in self:
            # Today's appointments
            today_appointments = self.env['salon.appointment'].search([
                ('appointment_date', '>=', today),
                ('appointment_date', '<', today + timedelta(days=1)),
                ('state', 'not in', ['cancelled', 'no_show'])
            ])
            dashboard.today_appointments = len(today_appointments)

            # Completed today
            completed_today = today_appointments.filtered(lambda a: a.state == 'completed')
            dashboard.today_completed = len(completed_today)

            # Today's orders and revenue
            today_orders = self.env['salon.order'].search([
                ('order_date', '>=', today),
                ('order_date', '<', today + timedelta(days=1)),
                ('state', '=', 'done')
            ])
            dashboard.today_orders = len(today_orders)
            dashboard.today_revenue = sum(today_orders.mapped('total_amount'))

            # Active staff (employees with appointments today)
            staff_with_appointments = today_appointments.mapped('employee_id')
            dashboard.active_staff = len(staff_with_appointments)

            # Staff on break (simplified - staff with no appointments for 2+ hours)
            dashboard.staff_on_break = 0  # Could be more complex logic

            # Chair statistics
            all_chairs = self.env['salon.chair'].search([('active', '=', True)])
            dashboard.available_chairs = len(all_chairs.filtered(lambda c: c.state == 'available'))
            dashboard.occupied_chairs = len(all_chairs.filtered(lambda c: c.state == 'occupied'))

            # Weekly revenue
            week_orders = self.env['salon.order'].search([
                ('order_date', '>=', start_of_week),
                ('order_date', '<', today + timedelta(days=1)),
                ('state', '=', 'done')
            ])
            dashboard.weekly_revenue = sum(week_orders.mapped('total_amount'))

            # Monthly revenue
            month_orders = self.env['salon.order'].search([
                ('order_date', '>=', start_of_month),
                ('order_date', '<', today + timedelta(days=1)),
                ('state', '=', 'done')
            ])
            dashboard.monthly_revenue = sum(month_orders.mapped('total_amount'))

            # Recent appointments (last 7 days)
            recent = self.env['salon.appointment'].search([
                ('appointment_date', '>=', today - timedelta(days=7)),
                ('state', 'not in', ['draft'])
            ], order='appointment_date desc', limit=10)
            dashboard.recent_appointment_ids = [(6, 0, recent.ids)]
            