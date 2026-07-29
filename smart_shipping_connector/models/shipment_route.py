from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ShippingShipmentRoute(models.Model):
    """Shipment Route Tracking"""
    _name = 'shipping.shipment.route'
    _description = 'Shipment Route'
    _order = 'shipment_id, sequence'
    _rec_name = 'location'

    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipment',
        required=True,
        ondelete='cascade',
    )

    sequence = fields.Integer(string='Sequence', default=10)

    location = fields.Char(string='Location', required=True)
    location_type = fields.Selection([
        ('origin', 'Origin'),
        ('hub', 'Hub'),
        ('sort_center', 'Sort Center'),
        ('transit', 'Transit Point'),
        ('destination', 'Destination'),
    ], string='Location Type', default='transit')

    arrival_date = fields.Datetime(string='Arrival Date')
    departure_date = fields.Datetime(string='Departure Date')

    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('arrived', 'Arrived'),
        ('departed', 'Departed'),
        ('delayed', 'Delayed'),
        ('completed', 'Completed'),
    ], string='Status', default='scheduled')

    notes = fields.Text(string='Notes')
    