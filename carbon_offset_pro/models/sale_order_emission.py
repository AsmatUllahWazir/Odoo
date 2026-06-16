from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    total_carbon_footprint_kg = fields.Float(string='Total CO2e (kg)', compute='_compute_carbon_footprint', store=True)
    total_carbon_footprint_tons = fields.Float(string='Total CO2e (tons)', compute='_compute_carbon_footprint',
                                               store=True)
    carbon_offset_amount_kg = fields.Float(string='Offset Amount (kg)', default=0.0)
    carbon_offset_amount_tons = fields.Float(string='Offset Amount (tons)', compute='_compute_offset_tons', store=True)
    offset_cost = fields.Monetary(string='Offset Cost', compute='_compute_offset_cost', store=True)
    offset_purchase_id = fields.Many2one('carbon.offset.purchase', string='Offset Purchase', readonly=True)
    is_fully_offset = fields.Boolean(string='Fully Offset', compute='_compute_offset_status', store=True)
    offset_percentage = fields.Float(string='Offset %', compute='_compute_offset_status', store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    sustainability_notes = fields.Text(string='Sustainability Notes')

    # Carbon Tier
    carbon_tier = fields.Selection([
        ('net_zero', '🌟 Net Zero (0-1kg)'),
        ('low', '✅ Low (1-10kg)'),
        ('medium', '📊 Medium (10-100kg)'),
        ('high', '⚠️ High (100-1000kg)'),
        ('very_high', '🚨 Very High (1000+kg)'),
    ], string='Carbon Tier', compute='_compute_carbon_tier', store=True)

    tier_color = fields.Char(string='Tier Color', compute='_compute_carbon_tier')

    @api.depends('order_line.product_id', 'order_line.product_uom_qty')
    def _compute_carbon_footprint(self):
        for order in self:
            total = 0.0
            for line in order.order_line:
                factor = self.env['carbon.offset.product.emission'].search([('product_id', '=', line.product_id.id)],
                                                                           limit=1)
                if factor:
                    total += factor.total_emission_kg * line.product_uom_qty
            order.total_carbon_footprint_kg = total
            order.total_carbon_footprint_tons = total / 1000

    @api.depends('carbon_offset_amount_kg')
    def _compute_offset_tons(self):
        for order in self:
            order.carbon_offset_amount_tons = order.carbon_offset_amount_kg / 1000

    @api.depends('carbon_offset_amount_kg')
    def _compute_offset_cost(self):
        for order in self:
            tons = order.carbon_offset_amount_kg / 1000
            if tons <= 1:
                price = 25.0
            elif tons <= 10:
                price = 20.0
            elif tons <= 50:
                price = 18.0
            elif tons <= 100:
                price = 15.0
            else:
                price = 12.0
            order.offset_cost = tons * price

    @api.depends('carbon_offset_amount_kg', 'total_carbon_footprint_kg')
    def _compute_offset_status(self):
        for order in self:
            if order.total_carbon_footprint_kg > 0:
                order.offset_percentage = (order.carbon_offset_amount_kg / order.total_carbon_footprint_kg) * 100
                order.is_fully_offset = order.carbon_offset_amount_kg >= order.total_carbon_footprint_kg
            else:
                order.offset_percentage = 100.0
                order.is_fully_offset = True

    @api.depends('total_carbon_footprint_kg')
    def _compute_carbon_tier(self):
        for order in self:
            kg = order.total_carbon_footprint_kg
            if kg < 1:
                order.carbon_tier = 'net_zero'
                order.tier_color = 'green'
            elif kg <= 10:
                order.carbon_tier = 'low'
                order.tier_color = 'lightgreen'
            elif kg <= 100:
                order.carbon_tier = 'medium'
                order.tier_color = 'orange'
            elif kg <= 1000:
                order.carbon_tier = 'high'
                order.tier_color = 'red'
            else:
                order.carbon_tier = 'very_high'
                order.tier_color = 'darkred'

    def action_open_offset_wizard(self):
        self.ensure_one()
        if self.total_carbon_footprint_kg <= 0:
            raise UserError(_("This order has no carbon footprint to offset."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Carbon Offset'),
            'res_model': 'carbon.offset.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_total_footprint_kg': self.total_carbon_footprint_kg,
                'default_total_footprint_tons': self.total_carbon_footprint_tons,
            }
        }

    def action_generate_sustainability_report(self):
        self.ensure_one()
        return self.env.ref('carbon_offset_pro.action_report_sustainability').report_action(self)


class SaleOrderLineInherit(models.Model):
    _inherit = 'sale.order.line'

    line_carbon_footprint_kg = fields.Float(string='Line CO2e (kg)', compute='_compute_line_footprint', store=True)
    carbon_rating = fields.Char(string='Carbon Rating', compute='_compute_line_footprint', store=True)

    @api.depends('product_id', 'product_uom_qty')
    def _compute_line_footprint(self):
        for line in self:
            factor = self.env['carbon.offset.product.emission'].search([('product_id', '=', line.product_id.id)],
                                                                       limit=1)
            if factor:
                line.line_carbon_footprint_kg = factor.total_emission_kg * line.product_uom_qty
                line.carbon_rating = factor.carbon_rating
            else:
                line.line_carbon_footprint_kg = 0.0
                line.carbon_rating = ''
                