from odoo import models, api, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class SustainabilityReportPDF(models.AbstractModel):
    _name = 'report.carbon_offset_pro.report_sustainability_template'
    _description = 'Sustainability Report PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Get report values for sustainability report"""
        # Filter out deleted records
        docs = self.env['sale.order'].browse(docids).exists()

        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': docs,
            'data': data,
            'get_date': self._get_date,
            'calculate_total_emissions': self._calculate_total_emissions,
            'get_emission_breakdown': self._get_emission_breakdown,
            'get_certificate_number': self._get_certificate_number,
            'get_carbon_tier_label': self._get_carbon_tier_label,
            'get_carbon_rating_icon': self._get_carbon_rating_icon,
        }

    def _get_date(self):
        """Get current date for report footer"""
        return datetime.now().strftime('%B %d, %Y')

    def _calculate_total_emissions(self, order):
        """Calculate total carbon emissions for an order"""
        if not order or not order.exists():
            return 0.0
        total = 0.0
        for line in order.order_line:
            if line.line_carbon_footprint_kg:
                total += line.line_carbon_footprint_kg
        return total

    def _get_emission_breakdown(self, order):
        """Get breakdown of emissions by product (top 10)"""
        if not order or not order.exists():
            return []
        breakdown = []
        for line in order.order_line:
            if line.line_carbon_footprint_kg > 0:
                breakdown.append({
                    'product': line.product_id.display_name or 'Unknown Product',
                    'quantity': line.product_uom_qty,
                    'emission_kg': line.line_carbon_footprint_kg
                })
        return sorted(breakdown, key=lambda x: x['emission_kg'], reverse=True)[:10]

    def _get_certificate_number(self, order):
        """Get certificate number if available"""
        if order and order.exists() and order.offset_purchase_id and order.offset_purchase_id.exists():
            return order.offset_purchase_id.certificate_number
        return 'Not Issued Yet'

    def _get_carbon_tier_label(self, tier):
        """Get human-readable carbon tier label"""
        tier_labels = {
            'net_zero': ('🌟 Net Zero', 'success'),
            'low': ('✅ Low', 'info'),
            'medium': ('📊 Medium', 'warning'),
            'high': ('⚠️ High', 'danger'),
            'very_high': ('🚨 Very High', 'danger'),
        }
        return tier_labels.get(tier, ('Unknown', 'secondary'))

    def _get_carbon_rating_icon(self, rating):
        """Get icon for carbon rating"""
        rating_icons = {
            'A++': '🏆 A++ (Best)',
            'A': '✅ A (Excellent)',
            'B': '👍 B (Good)',
            'C': '📊 C (Average)',
            'D': '⚠️ D (Poor)',
            'E': '🔴 E (Very Poor)',
        }
        return rating_icons.get(rating, 'N/A')


class CarbonCertificatePDF(models.AbstractModel):
    _name = 'report.carbon_offset_pro.report_certificate_template'
    _description = 'Carbon Offset Certificate PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Get report values for carbon offset certificate"""
        # Filter out deleted records
        docs = self.env['carbon.offset.purchase'].browse(docids).exists()

        # If no documents exist, return empty values to prevent error
        if not docs:
            return {
                'doc_ids': [],
                'doc_model': 'carbon.offset.purchase',
                'docs': docs,
                'data': data,
                'get_date': self._get_date,
                'get_equivalent_trees': self._get_equivalent_trees,
                'get_equivalent_cars': self._get_equivalent_cars,
                'get_equivalent_homes': self._get_equivalent_homes,
                'get_project_type_label': self._get_project_type_label,
                'get_certification_label': self._get_certification_label,
                'get_certificate_status': self._get_certificate_status,
                'no_docs': True,
            }

        return {
            'doc_ids': docids,
            'doc_model': 'carbon.offset.purchase',
            'docs': docs,
            'data': data,
            'get_date': self._get_date,
            'get_equivalent_trees': self._get_equivalent_trees,
            'get_equivalent_cars': self._get_equivalent_cars,
            'get_equivalent_homes': self._get_equivalent_homes,
            'get_project_type_label': self._get_project_type_label,
            'get_certification_label': self._get_certification_label,
            'get_certificate_status': self._get_certificate_status,
        }

    def _get_date(self):
        """Get current date for certificate footer"""
        return datetime.now().strftime('%B %d, %Y')

    def _get_equivalent_trees(self, tons_offset):
        """Calculate equivalent trees (average tree absorbs 22kg CO2 per year)"""
        try:
            trees_equivalent = (tons_offset * 1000) / 22
            return round(trees_equivalent)
        except (TypeError, ZeroDivisionError):
            return 0

    def _get_equivalent_cars(self, tons_offset):
        """Calculate equivalent cars (average car emits 4.6 tons CO2 per year)"""
        try:
            cars_equivalent = tons_offset / 4.6
            return round(cars_equivalent, 1)
        except (TypeError, ZeroDivisionError):
            return 0.0

    def _get_equivalent_homes(self, tons_offset):
        """Calculate equivalent homes (average home emits 7.5 tons CO2 per year)"""
        try:
            homes_equivalent = tons_offset / 7.5
            return round(homes_equivalent, 1)
        except (TypeError, ZeroDivisionError):
            return 0.0

    def _get_project_type_label(self, project_type):
        """Get human-readable project type label with emoji"""
        type_labels = {
            'reforestation': '🌳 Reforestation & Afforestation',
            'solar': '☀️ Solar Energy',
            'wind': '💨 Wind Energy',
            'methane': '🏭 Methane Capture',
            'cookstoves': '🍳 Clean Cookstoves',
            'blue_carbon': '🌊 Blue Carbon (Mangroves)',
        }
        return type_labels.get(project_type, project_type or 'Unknown')

    def _get_certification_label(self, certifying_body):
        """Get human-readable certification label"""
        cert_labels = {
            'vcs': 'Verified Carbon Standard (VCS)',
            'gs': 'Gold Standard',
            'acr': 'American Carbon Registry',
            'car': 'Climate Action Reserve',
        }
        return cert_labels.get(certifying_body, certifying_body or 'Unknown')

    def _get_certificate_status(self, purchase):
        """Get certificate status with icon"""
        if not purchase or not purchase.exists():
            return ('❌', 'Not Found')
        if purchase.certificate_issued:
            return ('✅', 'Issued')
        return ('⏳', 'Pending')


class ExecutiveSummaryPDF(models.AbstractModel):
    _name = 'report.carbon_offset_pro.report_executive_summary'
    _description = 'Executive Sustainability Summary PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Get report values for executive summary"""
        docs = self.env['sustainability.dashboard'].browse(docids).exists()

        return {
            'doc_ids': docids,
            'doc_model': 'sustainability.dashboard',
            'docs': docs,
            'data': data,
            'get_date': self._get_date,
            'get_monthly_trend': self._get_monthly_trend,
            'get_carbon_tier_distribution_chart': self._get_carbon_tier_distribution_chart,
            'calculate_total_emissions': self._calculate_total_emissions,
            'get_offset_recommendations': self._get_offset_recommendations,
        }

    def _get_date(self):
        """Get current date for report footer"""
        return datetime.now().strftime('%B %d, %Y')

    def _get_monthly_trend(self, report):
        """Get monthly emission trends for the report period"""
        if not report or not report.exists():
            return []
        monthly_data = {}
        orders = self.env['sale.order'].search([
            ('date_order', '>=', report.date_from),
            ('date_order', '<=', report.date_to),
            ('company_id', '=', report.company_id.id),
            ('state', 'in', ['sale', 'done'])
        ])

        for order in orders:
            if order and order.exists():
                month = order.date_order.strftime('%Y-%m')
                if month not in monthly_data:
                    monthly_data[month] = 0
                monthly_data[month] += order.total_carbon_footprint_kg

        return [{'month': k, 'emission_kg': v} for k, v in sorted(monthly_data.items())]

    def _get_carbon_tier_distribution_chart(self, report):
        """Get carbon tier distribution data for charts"""
        if not report or not report.exists():
            return []
        orders = self.env['sale.order'].search([
            ('date_order', '>=', report.date_from),
            ('date_order', '<=', report.date_to),
            ('company_id', '=', report.company_id.id),
            ('state', 'in', ['sale', 'done'])
        ])

        tier_counts = {'net_zero': 0, 'low': 0, 'medium': 0, 'high': 0, 'very_high': 0}
        for order in orders:
            if order and order.exists() and order.carbon_tier:
                tier_counts[order.carbon_tier] = tier_counts.get(order.carbon_tier, 0) + 1

        return [
            {'label': 'Net Zero (<1kg)', 'value': tier_counts['net_zero'], 'color': '#28a745'},
            {'label': 'Low (1-10kg)', 'value': tier_counts['low'], 'color': '#17a2b8'},
            {'label': 'Medium (10-100kg)', 'value': tier_counts['medium'], 'color': '#ffc107'},
            {'label': 'High (100-1000kg)', 'value': tier_counts['high'], 'color': '#fd7e14'},
            {'label': 'Very High (>1000kg)', 'value': tier_counts['very_high'], 'color': '#dc3545'},
        ]

    def _calculate_total_emissions(self, report):
        """Calculate total emissions for the report period"""
        if not report or not report.exists():
            return 0.0
        orders = self.env['sale.order'].search([
            ('date_order', '>=', report.date_from),
            ('date_order', '<=', report.date_to),
            ('company_id', '=', report.company_id.id),
            ('state', 'in', ['sale', 'done'])
        ])
        return sum(orders.mapped('total_carbon_footprint_kg'))

    def _get_offset_recommendations(self, report):
        """Get recommendations based on offset percentage"""
        if not report or not report.exists():
            return []
        recommendations = []

        if report.offset_percentage < 50:
            recommendations.append({
                'priority': 'High',
                'message': 'Increase carbon offset purchases. Current offset rate is only %.1f%%.' % report.offset_percentage,
                'action': 'Consider purchasing additional carbon offsets to reach carbon neutrality.'
            })

        if report.avg_co2_per_order > 100:
            recommendations.append({
                'priority': 'Medium',
                'message': 'High average emissions per order (%.1f kg).' % report.avg_co2_per_order,
                'action': 'Promote lower-carbon products and optimize shipping routes.'
            })

        if report.total_orders > 100:
            recommendations.append({
                'priority': 'Medium',
                'message': 'Large number of orders (%d) contributing to emissions.' % report.total_orders,
                'action': 'Consider consolidating shipments and implementing sustainable packaging.'
            })

        if report.offset_percentage >= 100:
            recommendations.append({
                'priority': 'Low',
                'message': 'Congratulations! You are carbon neutral! 🎉',
                'action': 'Continue maintaining your carbon offset program and consider reducing emissions at source.'
            })

        return recommendations
