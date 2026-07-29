from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ShippingTrackingEvent(models.Model):
    """Tracking History"""
    _name = 'shipping.tracking.event'
    _description = 'Shipping Tracking Event'
    _order = 'event_date desc'
    _rec_name = 'status_description'

    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipment',
        required=True,
        ondelete='cascade',
    )
    tracking_number = fields.Char(
        string='Tracking Number',
        related='shipment_id.tracking_number',
        store=True,
    )

    event_date = fields.Datetime(string='Event Date', required=True, default=fields.Datetime.now)
    event_code = fields.Char(string='Event Code')
    status_code = fields.Char(string='Status Code')
    status_description = fields.Char(string='Status Description', required=True)

    location = fields.Char(string='Location')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    country = fields.Char(string='Country')

    description = fields.Text(string='Event Description')
    raw_data = fields.Text(string='Raw Tracking Data')

    is_delivered = fields.Boolean(string='Delivered Event')
    is_exception = fields.Boolean(string='Exception Event')

    def action_view_shipment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipment'),
            'res_model': 'shipping.shipment',
            'res_id': self.shipment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    