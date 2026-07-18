# -*- coding: utf-8 -*-
"""
Dashboard Module for LIMS
Provides real-time analytics, KPIs, and performance metrics for laboratory operations
"""
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from collections import defaultdict
import logging

_logger = logging.getLogger(__name__)


class LimsDashboard(models.Model):
    """
    Comprehensive Dashboard Model
    Virtual model providing real-time analytics and KPIs
    """
    _name = 'lims.dashboard'
    _description = 'LIMS Dashboard'
    _auto = False

    # ===================== BASIC METRICS =====================
    total_orders = fields.Integer(string='Total Orders')
    total_patients = fields.Integer(string='Total Patients')
    total_samples = fields.Integer(string='Total Samples')
    total_reports = fields.Integer(string='Total Reports')

    # ===================== DAILY METRICS =====================
    today_orders = fields.Integer(string="Today's Orders")
    today_samples = fields.Integer(string="Today's Samples")
    today_reports = fields.Integer(string="Today's Reports")
    today_revenue = fields.Monetary(string="Today's Revenue")

    # ===================== PERIODIC METRICS =====================
    week_orders = fields.Integer(string='Weekly Orders')
    week_samples = fields.Integer(string='Weekly Samples')
    week_reports = fields.Integer(string='Weekly Reports')
    week_revenue = fields.Monetary(string='Weekly Revenue')

    month_orders = fields.Integer(string='Monthly Orders')
    month_samples = fields.Integer(string='Monthly Samples')
    month_reports = fields.Integer(string='Monthly Reports')
    month_revenue = fields.Monetary(string='Monthly Revenue')

    year_orders = fields.Integer(string='Yearly Orders')
    year_revenue = fields.Monetary(string='Yearly Revenue')

    # ===================== STATUS METRICS =====================
    pending_orders = fields.Integer(string='Pending Orders')
    pending_samples = fields.Integer(string='Pending Samples')
    abnormal_results = fields.Integer(string='Abnormal Results')
    critical_results = fields.Integer(string='Critical Results')

    # ===================== QUALITY METRICS =====================
    qc_passed = fields.Integer(string='QC Passed')
    qc_failed = fields.Integer(string='QC Failed')
    qc_pass_rate = fields.Float(string='QC Pass Rate')

    # ===================== PERFORMANCE METRICS =====================
    avg_turnaround = fields.Float(string='Average Turnaround Time (hours)')
    on_time_rate = fields.Float(string='On-Time Delivery Rate')
    completion_rate = fields.Float(string='Completion Rate')

    # ===================== REVENUE METRICS =====================
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id.id
    )

    def init(self):
        """Initialize dashboard view"""
        # This is a virtual model, no actual table creation needed
        pass

    @api.model
    def get_dashboard_data(self, period='month'):
        """
        Get comprehensive dashboard data
        Returns: dict with all dashboard metrics
        """
        Order = self.env['lims.test_order']
        Patient = self.env['lims.patient']
        Sample = self.env['lims.sample']
        Report = self.env['lims.report']
        QC = self.env['lims.quality_control']

        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        year_ago = today - timedelta(days=365)

        # Get all orders
        all_orders = Order.search([])

        # Base metrics
        data = {
            'total_orders': len(all_orders),
            'total_patients': Patient.search_count([]),
            'total_samples': Sample.search_count([]),
            'total_reports': Report.search_count([]),

            # Daily metrics
            'today_orders': Order.search_count([('date_ordered', '>=', today)]),
            'today_samples': Sample.search_count([('collection_date', '>=', today)]),
            'today_reports': Report.search_count([('report_date', '>=', today)]),
            'today_revenue': sum(Order.search([('date_ordered', '>=', today)]).mapped('amount_total')),

            # Weekly metrics
            'week_orders': Order.search_count([('date_ordered', '>=', week_ago)]),
            'week_samples': Sample.search_count([('collection_date', '>=', week_ago)]),
            'week_reports': Report.search_count([('report_date', '>=', week_ago)]),
            'week_revenue': sum(Order.search([('date_ordered', '>=', week_ago)]).mapped('amount_total')),

            # Monthly metrics
            'month_orders': Order.search_count([('date_ordered', '>=', month_ago)]),
            'month_samples': Sample.search_count([('collection_date', '>=', month_ago)]),
            'month_reports': Report.search_count([('report_date', '>=', month_ago)]),
            'month_revenue': sum(Order.search([('date_ordered', '>=', month_ago)]).mapped('amount_total')),

            # Yearly metrics
            'year_orders': Order.search_count([('date_ordered', '>=', year_ago)]),
            'year_revenue': sum(Order.search([('date_ordered', '>=', year_ago)]).mapped('amount_total')),

            # Status metrics
            'pending_orders': Order.search_count([('state', 'in', ['draft', 'confirmed', 'in_progress'])]),
            'pending_samples': Sample.search_count([('status', 'in', ['registered', 'collected', 'received'])]),
            'abnormal_results': self.env['lims.test_order_line'].search_count([('is_abnormal', '=', True)]),
            'critical_results': self.env['lims.test_order_line'].search_count([('is_critical', '=', True)]),

            # Quality metrics
            'qc_passed': QC.search_count([('is_passed', '=', True)]),
            'qc_failed': QC.search_count([('is_passed', '=', False)]),
        }

        # Calculate QC pass rate
        total_qc = data['qc_passed'] + data['qc_failed']
        data['qc_pass_rate'] = (data['qc_passed'] / total_qc * 100) if total_qc > 0 else 0

        # Performance metrics
        completed_orders = Order.search([('state', 'in', ['reported', 'invoiced', 'completed'])])
        data['completion_rate'] = (len(completed_orders) / len(all_orders) * 100) if all_orders else 0

        # Calculate average turnaround
        turnaround_hours = [o.actual_turnaround_hours for o in completed_orders if o.actual_turnaround_hours > 0]
        data['avg_turnaround'] = sum(turnaround_hours) / len(turnaround_hours) if turnaround_hours else 0

        # Calculate on-time rate
        on_time = completed_orders.filtered(lambda o: o.actual_turnaround_hours <= o.expected_turnaround_hours)
        data['on_time_rate'] = (len(on_time) / len(completed_orders) * 100) if completed_orders else 0

        return data

    @api.model
    def get_order_trends(self, days=30):
        """
        Get order trends for the specified period
        Returns: dict with daily order counts and revenue
        """
        today = datetime.now().date()
        start_date = today - timedelta(days=days)

        orders = self.env['lims.test_order'].search([
            ('date_ordered', '>=', start_date),
            ('state', '!=', 'cancelled')
        ])

        # Group by date
        daily_counts = defaultdict(int)
        daily_revenue = defaultdict(float)

        for order in orders:
            date_key = order.date_ordered.date()
            daily_counts[date_key] += 1
            daily_revenue[date_key] += order.amount_total

        # Sort by date
        dates = sorted(daily_counts.keys())

        return {
            'dates': [d.strftime('%Y-%m-%d') for d in dates],
            'orders': [daily_counts[d] for d in dates],
            'revenue': [daily_revenue[d] for d in dates],
            'total_orders': sum(daily_counts.values()),
            'total_revenue': sum(daily_revenue.values()),
            'avg_daily_orders': sum(daily_counts.values()) / len(dates) if dates else 0,
            'avg_daily_revenue': sum(daily_revenue.values()) / len(dates) if dates else 0,
        }

    @api.model
    def get_status_distribution(self):
        """
        Get distribution of orders by status
        Returns: dict with status counts
        """
        orders = self.env['lims.test_order'].search([])
        status_map = dict(orders._fields['state'].selection)

        distribution = {}
        for status in dict(orders._fields['state'].selection).keys():
            count = len(orders.filtered(lambda o: o.state == status))
            if count > 0:
                distribution[status_map.get(status, status)] = count

        return distribution

    @api.model
    def get_department_stats(self):
        """
        Get statistics by department
        Returns: dict with department-wise metrics
        """
        departments = dict(self.env['lims.test_order']._fields['department'].selection)
        stats = {}

        for dept_code, dept_name in departments.items():
            orders = self.env['lims.test_order'].search([('department', '=', dept_code)])
            stats[dept_name] = {
                'total_orders': len(orders),
                'completed': len(orders.filtered(lambda o: o.state in ['reported', 'invoiced', 'completed'])),
                'pending': len(orders.filtered(lambda o: o.state in ['draft', 'confirmed', 'in_progress'])),
                'revenue': sum(orders.mapped('amount_total')),
                'avg_turnaround': sum(orders.mapped('actual_turnaround_hours')) / max(len(orders), 1),
            }

        return stats

    @api.model
    def get_priority_stats(self):
        """
        Get statistics by priority
        Returns: dict with priority-wise metrics
        """
        priorities = dict(self.env['lims.test_order']._fields['priority'].selection)
        stats = {}

        for priority_code, priority_name in priorities.items():
            orders = self.env['lims.test_order'].search([('priority', '=', priority_code)])
            stats[priority_name] = {
                'total_orders': len(orders),
                'completed': len(orders.filtered(lambda o: o.state in ['reported', 'invoiced', 'completed'])),
                'pending': len(orders.filtered(lambda o: o.state in ['draft', 'confirmed', 'in_progress'])),
                'avg_turnaround': sum(orders.mapped('actual_turnaround_hours')) / max(len(orders), 1),
            }

        return stats

    @api.model
    def get_quality_metrics(self):
        """
        Get comprehensive quality metrics
        Returns: dict with quality statistics
        """
        QC = self.env['lims.quality_control']
        TestLine = self.env['lims.test_order_line']

        total_qc = QC.search_count([])
        passed_qc = QC.search_count([('is_passed', '=', True)])
        failed_qc = QC.search_count([('is_passed', '=', False)])

        # Get QC by type
        qc_types = dict(QC._fields['qc_type'].selection)
        qc_by_type = {}
        for type_code, type_name in qc_types.items():
            qcs = QC.search([('qc_type', '=', type_code)])
            qc_by_type[type_name] = {
                'total': len(qcs),
                'passed': len(qcs.filtered(lambda q: q.is_passed)),
                'failed': len(qcs.filtered(lambda q: not q.is_passed)),
                'pass_rate': (len(qcs.filtered(lambda q: q.is_passed)) / len(qcs) * 100) if qcs else 0,
            }

        # Get abnormal results by test type
        abnormal_lines = TestLine.search([('is_abnormal', '=', True)])
        abnormal_by_test = {}
        for line in abnormal_lines:
            test_name = line.test_type_id.name
            if test_name not in abnormal_by_test:
                abnormal_by_test[test_name] = 0
            abnormal_by_test[test_name] += 1

        return {
            'total_qc': total_qc,
            'passed_qc': passed_qc,
            'failed_qc': failed_qc,
            'pass_rate': (passed_qc / total_qc * 100) if total_qc > 0 else 0,
            'qc_by_type': qc_by_type,
            'abnormal_by_test': abnormal_by_test,
            'total_abnormal': len(abnormal_lines),
            'total_critical': TestLine.search_count([('is_critical', '=', True)]),
        }

    @api.model
    def get_financial_summary(self, period='month'):
        """
        Get financial summary for the specified period
        Returns: dict with financial metrics
        """
        today = datetime.now().date()

        if period == 'today':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)

        invoices = self.env['account.move'].search([
            ('invoice_date', '>=', start_date),
            ('move_type', '=', 'out_invoice'),
            ('state', '!=', 'cancel')
        ])

        return {
            'total_invoices': len(invoices),
            'total_amount': sum(invoices.mapped('amount_total')),
            'paid_amount': sum(invoices.filtered(lambda i: i.payment_state == 'paid').mapped('amount_total')),
            'unpaid_amount': sum(invoices.filtered(lambda i: i.payment_state != 'paid').mapped('amount_total')),
            'average_invoice': sum(invoices.mapped('amount_total')) / len(invoices) if invoices else 0,
            'invoice_count_by_status': {
                'draft': len(invoices.filtered(lambda i: i.state == 'draft')),
                'posted': len(invoices.filtered(lambda i: i.state == 'posted')),
                'paid': len(invoices.filtered(lambda i: i.payment_state == 'paid')),
                'unpaid': len(invoices.filtered(lambda i: i.payment_state != 'paid')),
            }
        }

    @api.model
    def get_patient_metrics(self):
        """
        Get patient-related metrics
        Returns: dict with patient statistics
        """
        Patient = self.env['lims.patient']
        patients = Patient.search([])

        gender_dist = {}
        for gender in dict(Patient._fields['gender'].selection).keys():
            count = len(patients.filtered(lambda p: p.gender == gender))
            if count > 0:
                gender_dist[dict(Patient._fields['gender'].selection).get(gender, gender)] = count

        age_groups = {}
        for age_group in dict(Patient._fields['age_group'].selection).keys():
            count = len(patients.filtered(lambda p: p.age_group == age_group))
            if count > 0:
                age_groups[dict(Patient._fields['age_group'].selection).get(age_group, age_group)] = count

        return {
            'total_patients': len(patients),
            'active_patients': len(patients.filtered(lambda p: p.active)),
            'gender_distribution': gender_dist,
            'age_group_distribution': age_groups,
            'avg_orders_per_patient': sum(patients.mapped('total_orders')) / len(patients) if patients else 0,
            'patients_with_abnormal': len(patients.filtered(lambda p: p.abnormal_results_count > 0)),
        }

    @api.model
    def get_sample_metrics(self):
        """
        Get sample-related metrics
        Returns: dict with sample statistics
        """
        Sample = self.env['lims.sample']
        samples = Sample.search([])

        status_dist = {}
        for status in dict(Sample._fields['status'].selection).keys():
            count = len(samples.filtered(lambda s: s.status == status))
            if count > 0:
                status_dist[dict(Sample._fields['status'].selection).get(status, status)] = count

        type_dist = {}
        for sample_type in dict(Sample._fields['sample_type'].selection).keys():
            count = len(samples.filtered(lambda s: s.sample_type == sample_type))
            if count > 0:
                type_dist[dict(Sample._fields['sample_type'].selection).get(sample_type, sample_type)] = count

        return {
            'total_samples': len(samples),
            'status_distribution': status_dist,
            'type_distribution': type_dist,
            'quality_ok': len(samples.filtered(lambda s: s.quality_ok)),
            'quality_not_ok': len(samples.filtered(lambda s: not s.quality_ok)),
            'expired_samples': len(samples.filtered(lambda s: s.is_expired)),
            'avg_collection_to_analysis': 0,  # Would need to compute
        }
    