from odoo import models, fields, api, _
from datetime import datetime


class SustainabilityDashboard(models.TransientModel):
    _name = 'sustainability.dashboard'
    _description = 'Sustainability Dashboard'

    date_from = fields.Date(string='From Date', default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='To Date', default=fields.Date.today)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # KPI Metrics
    total_co2_kg = fields.Float(string='Total CO2e (kg)', compute='_compute_metrics')
    total_co2_tons = fields.Float(string='Total CO2e (tons)', compute='_compute_metrics')
    total_orders = fields.Integer(string='Total Orders', compute='_compute_metrics')
    avg_co2_per_order = fields.Float(string='Avg CO2e per Order (kg)', compute='_compute_metrics')
    total_offset_kg = fields.Float(string='Total Offset (kg)', compute='_compute_metrics')
    total_offset_tons = fields.Float(string='Total Offset (tons)', compute='_compute_metrics')
    offset_percentage = fields.Float(string='Offset Percentage', compute='_compute_metrics')
    total_offset_cost = fields.Monetary(string='Total Offset Cost', compute='_compute_metrics',
                                        currency_field='currency_id')

    # Analysis Data
    top_emitting_products = fields.Text(string='Top Emitting Products', compute='_compute_metrics')
    top_emitting_customers = fields.Text(string='Top Emitting Customers', compute='_compute_metrics')
    monthly_trends = fields.Text(string='Monthly Trends', compute='_compute_metrics')
    carbon_tier_distribution = fields.Text(string='Carbon Tier Distribution', compute='_compute_metrics')

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_metrics(self):
        for dashboard in self:
            # Get orders in period
            orders = self.env['sale.order'].search([
                ('date_order', '>=', dashboard.date_from),
                ('date_order', '<=', dashboard.date_to),
                ('company_id', '=', dashboard.company_id.id),
                ('state', 'in', ['sale', 'done'])
            ])

            # Basic metrics
            dashboard.total_orders = len(orders)
            dashboard.total_co2_kg = sum(orders.mapped('total_carbon_footprint_kg'))
            dashboard.total_co2_tons = dashboard.total_co2_kg / 1000
            dashboard.avg_co2_per_order = dashboard.total_co2_kg / dashboard.total_orders if dashboard.total_orders else 0
            dashboard.total_offset_kg = sum(orders.mapped('carbon_offset_amount_kg'))
            dashboard.total_offset_tons = dashboard.total_offset_kg / 1000
            dashboard.offset_percentage = (
                        dashboard.total_offset_kg / dashboard.total_co2_kg * 100) if dashboard.total_co2_kg > 0 else 0
            dashboard.total_offset_cost = sum(orders.mapped('offset_cost'))

            # Top emitting products
            product_emissions = {}
            for order in orders:
                for line in order.order_line:
                    if line.line_carbon_footprint_kg > 0:
                        product_name = line.product_id.display_name or 'Unknown Product'
                        product_emissions[product_name] = product_emissions.get(product_name,
                                                                                0) + line.line_carbon_footprint_kg

            sorted_products = sorted(product_emissions.items(), key=lambda x: x[1], reverse=True)[:5]
            dashboard.top_emitting_products = '\n'.join(
                [f"{i + 1}. {name}: {emission:.1f} kg" for i, (name, emission) in enumerate(sorted_products)])

            # Top emitting customers
            customer_emissions = {}
            for order in orders:
                customer_name = order.partner_id.display_name or 'Unknown Customer'
                customer_emissions[customer_name] = customer_emissions.get(customer_name,
                                                                           0) + order.total_carbon_footprint_kg

            sorted_customers = sorted(customer_emissions.items(), key=lambda x: x[1], reverse=True)[:5]
            dashboard.top_emitting_customers = '\n'.join(
                [f"{i + 1}. {name}: {emission:.1f} kg" for i, (name, emission) in enumerate(sorted_customers)])

            # Monthly trends
            monthly_data = {}
            for order in orders:
                month = order.date_order.strftime('%Y-%m')
                monthly_data[month] = monthly_data.get(month, 0) + order.total_carbon_footprint_kg

            sorted_months = sorted(monthly_data.items())
            dashboard.monthly_trends = '\n'.join([f"{month}: {emission:.0f} kg" for month, emission in sorted_months])

            # Carbon tier distribution
            tier_counts = {'net_zero': 0, 'low': 0, 'medium': 0, 'high': 0, 'very_high': 0}
            for order in orders:
                if order.carbon_tier:
                    tier_counts[order.carbon_tier] = tier_counts.get(order.carbon_tier, 0) + 1

            dashboard.carbon_tier_distribution = '\n'.join([
                f"🌟 Net Zero (<1kg): {tier_counts['net_zero']} orders",
                f"✅ Low (1-10kg): {tier_counts['low']} orders",
                f"📊 Medium (10-100kg): {tier_counts['medium']} orders",
                f"⚠️ High (100-1000kg): {tier_counts['high']} orders",
                f"🚨 Very High (>1000kg): {tier_counts['very_high']} orders"
            ])

    def action_refresh(self):
        self._compute_metrics()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sustainability.dashboard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_export_report(self):
        self.ensure_one()
        # Generate PDF report for the dashboard
        return self.env.ref('carbon_offset_pro.action_report_carbon_certificate').report_action(self)
