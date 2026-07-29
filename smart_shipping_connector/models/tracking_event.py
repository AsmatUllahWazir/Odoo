from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ShippingTrackingEvent(models.Model):
    """Enhanced Tracking Event"""
    _name = 'shipping.tracking.event'
    _description = 'Shipping Tracking Event'
    _order = 'event_date desc'
    _rec_name = 'status_description'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipment',
        ondelete='cascade',
    )
    return_id = fields.Many2one(
        'shipping.return',
        string='Return',
        ondelete='cascade',
    )

    tracking_number = fields.Char(
        string='Tracking Number',
        required=True,
        index=True,
    )

    event_date = fields.Datetime(
        string='Event Date',
        required=True,
        default=fields.Datetime.now,
        index=True,
    )
    event_code = fields.Char(string='Event Code')
    status_code = fields.Char(string='Status Code')
    status_description = fields.Char(string='Status Description', required=True)

    location = fields.Char(string='Location')
    city = fields.Char(string='City')
    state = fields.Char(string='State')
    country = fields.Char(string='Country')
    postal_code = fields.Char(string='Postal Code')

    latitude = fields.Float(string='Latitude')
    longitude = fields.Float(string='Longitude')

    description = fields.Text(string='Event Description')
    raw_data = fields.Text(string='Raw Tracking Data')

    is_delivered = fields.Boolean(string='Delivered Event')
    is_exception = fields.Boolean(string='Exception Event')
    is_signature_required = fields.Boolean(string='Signature Required')
    signed_by = fields.Char(string='Signed By')

    # Additional Metadata
    service_area = fields.Char(string='Service Area')
    courier = fields.Char(string='Courier Name')
    courier_id = fields.Char(string='Courier ID')

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.model
    def create(self, vals):
        event = super(ShippingTrackingEvent, self).create(vals)

        # Update parent shipment status if needed
        if event.shipment_id:
            if event.is_delivered and event.shipment_id.state != 'delivered':
                event.shipment_id.action_mark_delivered()
            elif event.is_exception and event.shipment_id.state != 'exception':
                event.shipment_id.action_mark_exception()

        return event

    def action_view_shipment(self):
        """View related shipment"""
        self.ensure_one()
        if self.shipment_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Shipment'),
                'res_model': 'shipping.shipment',
                'res_id': self.shipment_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def action_cleanup_old_events(self):
        """Clean up old tracking events"""
        cutoff_date = fields.Datetime.now() - timedelta(days=180)
        old_events = self.search([
            ('create_date', '<', cutoff_date),
        ])
        count = old_events.unlink()
        _logger.info(f"Cleaned {count} old tracking events")
        return True
