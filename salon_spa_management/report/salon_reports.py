# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import base64


class SalonAppointmentReport(models.AbstractModel):
    _name = 'report.salon_spa_management.salon_appointment_report'
    _description = 'Salon Appointment Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['salon.appointment'].browse(docids)
        company = self.env.company

        # Format currency helper
        def format_currency(amount):
            if not amount:
                return '0.00'
            return f"{amount:,.2f}"

        return {
            'doc_ids': docids,
            'doc_model': 'salon.appointment',
            'docs': docs,
            'company': company,
            'data': data,
            'datetime': datetime,
            'format_currency': format_currency,
            'format_date': lambda d: d.strftime('%B %d, %Y at %I:%M %p') if d else '',
        }


class SalonOrderReport(models.AbstractModel):
    _name = 'report.salon_spa_management.salon_order_report'
    _description = 'Salon Order Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['salon.order'].browse(docids)
        company = self.env.company

        def format_currency(amount):
            if not amount:
                return '0.00'
            return f"{amount:,.2f}"

        return {
            'doc_ids': docids,
            'doc_model': 'salon.order',
            'docs': docs,
            'company': company,
            'data': data,
            'datetime': datetime,
            'format_currency': format_currency,
        }


class SalonCommissionReport(models.AbstractModel):
    _name = 'report.salon_spa_management.salon_commission_report'
    _description = 'Salon Commission Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['salon.employee.commission'].browse(docids)
        company = self.env.company

        def format_currency(amount):
            if not amount:
                return '0.00'
            return f"{amount:,.2f}"

        # Calculate additional stats for each commission record
        for doc in docs:
            # Get orders for this commission
            orders = doc.order_ids.filtered(lambda o: o.state == 'done')
            # doc.total_orders_count = len(orders)
            # doc.total_revenue_amount = sum(orders.mapped('total_amount'))
            # doc.total_commission_amount = sum(orders.mapped('total_commission'))

            # Calculate commission rate
            # if doc.total_revenue_amount > 0:
            #     doc.commission_rate = (doc.total_commission_amount / doc.total_revenue_amount) * 100
            # else:
            #     doc.commission_rate = 0.0

        return {
            'doc_ids': docids,
            'doc_model': 'salon.employee.commission',
            'docs': docs,
            'company': company,
            'data': data,
            'datetime': datetime,
            'format_currency': format_currency,
            'format_date': lambda d: d.strftime('%B %d, %Y') if d else '',
        }


class SalonRevenueReport(models.AbstractModel):
    _name = 'report.salon_spa_management.salon_revenue_report'
    _description = 'Salon Revenue Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env.company

        def format_currency(amount):
            if not amount:
                return '0.00'
            return f"{amount:,.2f}"

        # Get date range from data or default to current month
        date_from = data.get('date_from') if data else None
        date_to = data.get('date_to') if data else None

        if not date_from:
            date_from = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        if not date_to:
            date_to = datetime.now().strftime('%Y-%m-%d')

        # Get orders in date range
        orders = self.env['salon.order'].search([
            ('order_date', '>=', date_from),
            ('order_date', '<=', date_to),
            ('state', '=', 'done')
        ])

        # Calculate statistics
        total_revenue = sum(orders.mapped('total_amount'))
        total_orders = len(orders)
        total_commission = sum(orders.mapped('total_commission'))
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

        # Group by service
        service_stats = {}
        for order in orders:
            for line in order.order_line_ids:
                service_name = line.service_id.name
                if service_name not in service_stats:
                    service_stats[service_name] = {
                        'count': 0,
                        'revenue': 0,
                        'commission': 0
                    }
                service_stats[service_name]['count'] += int(line.quantity)
                service_stats[service_name]['revenue'] += line.price_subtotal
                service_stats[service_name]['commission'] += line.commission_amount or 0

        # Group by staff
        staff_stats = {}
        for order in orders:
            if order.employee_id:
                staff_name = order.employee_id.name
                if staff_name not in staff_stats:
                    staff_stats[staff_name] = {
                        'orders': 0,
                        'revenue': 0,
                        'commission': 0
                    }
                staff_stats[staff_name]['orders'] += 1
                staff_stats[staff_name]['revenue'] += order.total_amount
                staff_stats[staff_name]['commission'] += order.total_commission or 0

        # Daily breakdown
        daily_stats = {}
        for order in orders:
            date_key = order.order_date.strftime('%Y-%m-%d')
            if date_key not in daily_stats:
                daily_stats[date_key] = {
                    'orders': 0,
                    'revenue': 0
                }
            daily_stats[date_key]['orders'] += 1
            daily_stats[date_key]['revenue'] += order.total_amount

        # Sort daily stats by date
        sorted_daily = dict(sorted(daily_stats.items()))

        return {
            'doc_ids': [],
            'doc_model': 'salon.revenue.report',
            'docs': [],
            'company': company,
            'data': data,
            'date_from': date_from,
            'date_to': date_to,
            'orders': orders,
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'total_commission': total_commission,
            'avg_order_value': avg_order_value,
            'service_stats': service_stats,
            'staff_stats': staff_stats,
            'daily_stats': sorted_daily,
            'datetime': datetime,
            'format_currency': format_currency,
        }


class SalonMembershipReport(models.AbstractModel):
    _name = 'report.salon_spa_management.salon_membership_report'
    _description = 'Salon Membership Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env.company

        def format_currency(amount):
            if not amount:
                return '0.00'
            return f"{amount:,.2f}"

        # Get all active memberships
        members = self.env['res.partner'].search([
            ('is_member', '=', True)
        ])

        total_members = len(members)
        active_members = len(
            members.filtered(lambda p: p.membership_card_id and p.membership_card_id.state == 'active'))

        # Group by membership plan
        plan_stats = {}
        for member in members:
            plan_name = member.membership_id.name or 'No Plan'
            if plan_name not in plan_stats:
                plan_stats[plan_name] = 0
            plan_stats[plan_name] += 1

        # Expiring soon (within 30 days)
        expiring_soon = members.filtered(
            lambda p: p.membership_expiry_date and
                      (p.membership_expiry_date - fields.Date.today()).days <= 30 and
                      (p.membership_expiry_date - fields.Date.today()).days >= 0
        )

        # Total revenue from members
        member_orders = self.env['salon.order'].search([
            ('partner_id', 'in', members.ids),
            ('state', '=', 'done')
        ])
        total_member_revenue = sum(member_orders.mapped('total_amount'))

        return {
            'doc_ids': [],
            'doc_model': 'salon.membership.report',
            'docs': [],
            'company': company,
            'data': data,
            'total_members': total_members,
            'active_members': active_members,
            'plan_stats': plan_stats,
            'expiring_soon': expiring_soon,
            'total_member_revenue': total_member_revenue,
            'members': members,
            'datetime': datetime,
            'format_currency': format_currency,
        }


class SalonDailyReport(models.AbstractModel):
    _name = 'report.salon_spa_management.salon_daily_report'
    _description = 'Salon Daily Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env.company

        def format_currency(amount):
            if not amount:
                return '0.00'
            return f"{amount:,.2f}"

        # Get date from data or default to today
        report_date_str = data.get('report_date') if data else None
        if report_date_str:
            report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
        else:
            report_date = fields.Date.today()

        # Get appointments for the day
        appointments = self.env['salon.appointment'].search([
            ('appointment_date', '>=', report_date),
            ('appointment_date', '<', report_date + timedelta(days=1))
        ])

        # Get orders for the day
        orders = self.env['salon.order'].search([
            ('order_date', '>=', report_date),
            ('order_date', '<', report_date + timedelta(days=1)),
            ('state', '=', 'done')
        ])

        # Statistics
        total_appointments = len(appointments)
        completed_appointments = len(appointments.filtered(lambda a: a.state == 'completed'))
        cancelled_appointments = len(appointments.filtered(lambda a: a.state == 'cancelled'))
        no_show_appointments = len(appointments.filtered(lambda a: a.state == 'no_show'))

        total_revenue = sum(orders.mapped('total_amount'))
        total_orders = len(orders)

        # Staff performance for the day
        staff_performance = {}
        for appointment in appointments.filtered(lambda a: a.state in ['completed', 'in_progress']):
            staff_name = appointment.employee_id.name
            if staff_name not in staff_performance:
                staff_performance[staff_name] = {
                    'appointments': 0,
                    'revenue': 0,
                }
            staff_performance[staff_name]['appointments'] += 1

        # Add revenue from orders
        for order in orders:
            if order.employee_id:
                staff_name = order.employee_id.name
                if staff_name in staff_performance:
                    staff_performance[staff_name]['revenue'] += order.total_amount
                else:
                    staff_performance[staff_name] = {
                        'appointments': 0,
                        'revenue': order.total_amount,
                    }

        # Chair utilization
        chairs = self.env['salon.chair'].search([('active', '=', True)])
        chair_stats = {}
        for chair in chairs:
            chair_orders = orders.filtered(lambda o: o.appointment_id and o.appointment_id.chair_id.id == chair.id)
            chair_stats[chair.name] = {
                'orders': len(chair_orders),
                'revenue': sum(chair_orders.mapped('total_amount')),
            }

        return {
            'doc_ids': [],
            'doc_model': 'salon.daily.report',
            'docs': [],
            'company': company,
            'data': data,
            'report_date': report_date,
            'appointments': appointments,
            'orders': orders,
            'total_appointments': total_appointments,
            'completed_appointments': completed_appointments,
            'cancelled_appointments': cancelled_appointments,
            'no_show_appointments': no_show_appointments,
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'staff_performance': staff_performance,
            'chair_stats': chair_stats,
            'datetime': datetime,
            'format_currency': format_currency,
        }
