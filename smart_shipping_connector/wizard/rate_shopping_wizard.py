from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RateShoppingWizard(models.TransientModel):
    _name = 'shipping.rate.request'
    _inherit = 'shipping.rate.request'
    _description = 'Rate Shopping Wizard'

    def action_get_rates(self):
        """Get rates from carriers"""
        self.ensure_one()
        self.state = 'requesting'

        try:
            # Clear existing rates
            self.rate_ids.unlink()

            # Get carriers to query
            carriers = self.carrier_ids
            if not carriers:
                carriers = self.env['shipping.carrier.provider'].search([
                    ('active', '=', True),
                    ('supports_rate_shopping', '=', True)
                ])

            if not carriers:
                raise UserError(_('No active carriers found with rate shopping support.'))

            shipment = self.shipment_id

            # Create dummy rates for demo
            rate_count = 0
            for carrier in carriers:
                account = carrier.account_ids.filtered(lambda a: a.environment in ['production', 'sandbox'])[:1]
                if account:
                    rate_count += 1
                    rate_vals = {
                        'shipment_id': shipment.id,
                        'carrier_provider_id': carrier.id,
                        'carrier_account_id': account.id,
                        'rate_request_id': f'shipping.rate.request,{self.id}',
                        'service_name': f"{carrier.name} - Standard",
                        'service_code': 'STANDARD',
                        'service_description': f"Standard shipping service from {carrier.name}",
                        'total_cost': 10.00 + (rate_count * 5.00),
                        'base_cost': 8.00 + (rate_count * 4.00),
                        'fuel_surcharge': 2.00 + (rate_count * 1.00),
                        'delivery_days': max(1, 5 - rate_count),
                        'currency_id': self.env.company.currency_id.id,
                    }
                    if self.include_fuel_surcharge:
                        rate_vals['fuel_surcharge'] = rate_vals['total_cost'] * 0.10
                    if self.include_residential and shipment.residential_delivery:
                        rate_vals['residential_surcharge'] = 2.00

                    self.env['shipping.rate'].create(rate_vals)

            if rate_count == 0:
                raise UserError(_('No active carrier accounts found. Please configure carrier accounts first.'))

            self.state = 'completed'
            self.response_date = fields.Datetime.now()

            return {
                'type': 'ir.actions.act_window',
                'name': _('Rate Shopping Results'),
                'res_model': 'shipping.rate.request',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        except UserError:
            self.state = 'failed'
            raise
        except Exception as e:
            self.state = 'failed'
            self.error_message = str(e)
            raise UserError(_('Failed to get rates: %s') % str(e))
        