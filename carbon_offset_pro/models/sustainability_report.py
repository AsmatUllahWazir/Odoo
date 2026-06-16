from odoo import models, fields, api


class SustainabilityReport(models.Model):
    _name = 'sustainability.report'
    _description = 'Sustainability Report'
    _rec_name = 'name'

    name = fields.Char(string='Report Name', default=lambda self: f"Report {fields.Date.today()}")
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    total_co2_kg = fields.Float(string='Total CO2e (kg)', compute='_compute_metrics')
    total_co2_tons = fields.Float(string='Total CO2e (tons)', compute='_compute_metrics')
    total_orders = fields.Integer(string='Total Orders', compute='_compute_metrics')
    offset_percentage = fields.Float(string='Offset Percentage', compute='_compute_metrics')

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_metrics(self):
        for report in self:
            orders = self.env['sale.order'].search([
                ('date_order', '>=', report.date_from),
                ('date_order', '<=', report.date_to),
                ('company_id', '=', report.company_id.id),
                ('state', 'in', ['sale', 'done'])
            ])
            report.total_orders = len(orders)
            report.total_co2_kg = sum(orders.mapped('total_carbon_footprint_kg'))
            report.total_co2_tons = report.total_co2_kg / 1000
            total_offset = sum(orders.mapped('carbon_offset_amount_kg'))
            report.offset_percentage = (total_offset / report.total_co2_kg * 100) if report.total_co2_kg > 0 else 0
