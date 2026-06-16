from odoo import http
from odoo.http import request


class CarbonOffsetController(http.Controller):

    @http.route('/carbon-offset/get_stats', type='json', auth='user')
    def get_stats(self):
        orders = request.env['sale.order'].search([('state', 'in', ['sale', 'done'])])
        total_emissions = sum(orders.mapped('total_carbon_footprint_kg'))
        total_offset = sum(orders.mapped('carbon_offset_amount_kg'))
        return {
            'total_emissions_kg': total_emissions,
            'total_offset_kg': total_offset,
            'offset_percentage': (total_offset / total_emissions * 100) if total_emissions > 0 else 0,
        }