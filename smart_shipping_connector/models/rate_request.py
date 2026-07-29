from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ShippingRateRequestHistory(models.Model):
    """Rate Request History - Store all rate requests"""
    _name = 'shipping.rate.request.history'
    _description = 'Rate Request History'
    _order = 'create_date desc'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        default=lambda self: _('New'),
        required=True,
    )

    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipment',
        required=True,
    )

    request_date = fields.Datetime(
        string='Request Date',
        default=fields.Datetime.now,
        required=True,
    )
    response_date = fields.Datetime(string='Response Date')

    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ], string='Status', default='pending', tracking=True)

    carrier_count = fields.Integer(
        string='Carriers Queried',
        help='Number of carriers queried'
    )
    rate_count = fields.Integer(
        string='Rates Retrieved',
        help='Number of rates retrieved'
    )

    response_time_ms = fields.Integer(
        string='Response Time (ms)',
        help='Total response time in milliseconds'
    )

    request_data = fields.Text(string='Request Data')
    response_data = fields.Text(string='Response Data')
    error_message = fields.Text(string='Error Message')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.rate.request.history') or _('New')
        return super(ShippingRateRequestHistory, self).create(vals)

    def action_view_rates(self):
        """View rates from this request"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rates'),
            'res_model': 'shipping.rate',
            'view_mode': 'tree,form',
            'domain': [('rate_request_id', '=', self.id)],
        }

    def action_view_shipment(self):
        """View related shipment"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipment'),
            'res_model': 'shipping.shipment',
            'res_id': self.shipment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    