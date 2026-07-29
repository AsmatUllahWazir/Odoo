from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipping Shipment',
        tracking=True,
        help='Associated shipping shipment'
    )
    has_shipping = fields.Boolean(
        string='Has Shipping',
        compute='_compute_has_shipping',
        store=True,
        help='Whether this picking has a shipping shipment'
    )

    @api.depends('shipment_id')
    def _compute_has_shipping(self):
        for picking in self:
            picking.has_shipping = bool(picking.shipment_id)

    def action_create_shipment(self):
        """Create shipping shipment from stock picking"""
        self.ensure_one()

        if self.shipment_id:
            return self.shipment_id.action_get_rates()

        if not self.partner_id:
            raise UserError(_('No customer selected for this picking.'))

        address = ""
        if self.partner_id:
            address = self.partner_id.street or ''
            if self.partner_id.city:
                address += f"\n{self.partner_id.city}"
            if self.partner_id.country_id:
                address += f"\n{self.partner_id.country_id.name}"

        # Get default carrier from config
        config = self.env['shipping.config']._get_default_config()
        carrier_id = config.default_carrier_provider_id.id if config else False
        account_id = config.default_carrier_account_id.id if config else False

        vals = {
            'stock_picking_id': self.id,
            'sale_order_id': self.sale_id.id if self.sale_id else False,
            'shipper_name': self.picking_type_id.warehouse_id.partner_id.name or self.env.company.name,
            'shipper_address': self.picking_type_id.warehouse_id.partner_id.street or '',
            'recipient_name': self.partner_id.name or '',
            'recipient_address': address,
            'recipient_phone': self.partner_id.phone or '',
            'recipient_email': self.partner_id.email or '',
            'is_international': self.partner_id.country_id and self.partner_id.country_id.code != self.env.company.country_id.code,
            'carrier_provider_id': carrier_id,
            'carrier_account_id': account_id,
        }

        shipment = self.env['shipping.shipment'].create(vals)
        self.shipment_id = shipment.id

        return shipment.action_get_rates()

    def action_view_shipment(self):
        """View related shipment"""
        self.ensure_one()
        if not self.shipment_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Shipment'),
                    'message': _('This picking does not have a shipping shipment.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipment'),
            'res_model': 'shipping.shipment',
            'res_id': self.shipment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
