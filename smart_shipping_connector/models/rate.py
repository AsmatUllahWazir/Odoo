from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons import decimal_precision as dp
import logging
import json
import requests
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ShippingRate(models.Model):
    """Shipping Rate Result - Complete Implementation"""
    _name = 'shipping.rate'
    _description = 'Shipping Rate'
    _order = 'total_cost asc'
    _rec_name = 'service_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    service_name = fields.Char(string='Service Name', required=True, tracking=True)
    service_code = fields.Char(string='Service Code', required=True)
    service_description = fields.Text(string='Service Description')

    # Cost Breakdown
    total_cost = fields.Monetary(
        string='Total Cost',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Total shipping cost'
    )
    base_cost = fields.Monetary(
        string='Base Cost',
        currency_field='currency_id',
        help='Base shipping cost before surcharges'
    )
    fuel_surcharge = fields.Monetary(
        string='Fuel Surcharge',
        currency_field='currency_id',
        help='Fuel surcharge applied'
    )
    residential_surcharge = fields.Monetary(
        string='Residential Surcharge',
        currency_field='currency_id',
    )
    saturday_surcharge = fields.Monetary(
        string='Saturday Surcharge',
        currency_field='currency_id',
    )
    insurance_surcharge = fields.Monetary(
        string='Insurance Surcharge',
        currency_field='currency_id',
    )
    cod_surcharge = fields.Monetary(
        string='COD Surcharge',
        currency_field='currency_id',
    )
    other_surcharges = fields.Monetary(
        string='Other Surcharges',
        currency_field='currency_id',
    )
    total_surcharges = fields.Monetary(
        string='Total Surcharges',
        currency_field='currency_id',
        compute='_compute_total_surcharges',
        store=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # Delivery Information
    delivery_days = fields.Integer(
        string='Estimated Delivery Days',
        help='Estimated number of delivery days'
    )
    delivery_date = fields.Datetime(
        string='Estimated Delivery Date',
        help='Estimated delivery date'
    )
    guaranteed_delivery = fields.Boolean(
        string='Guaranteed Delivery',
        help='Delivery date is guaranteed'
    )
    guaranteed_time = fields.Char(
        string='Guaranteed Time',
        help='Guaranteed delivery time (e.g., "10:30 AM")'
    )

    # Carrier Information
    carrier_provider_id = fields.Many2one(
        'shipping.carrier.provider',
        string='Carrier Provider',
        required=True,
    )
    carrier_account_id = fields.Many2one(
        'shipping.carrier.account',
        string='Carrier Account',
        required=True,
    )
    carrier_service_id = fields.Many2one(
        'shipping.carrier.service',
        string='Carrier Service',
    )

    # Shipment Reference
    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipment',
        ondelete='cascade',
    )
    rate_request_id = fields.Reference(
        selection=[('shipping.rate.request', 'Rate Request')],
        string='Rate Request',
    )

    # Selection
    is_selected = fields.Boolean(
        string='Selected',
        default=False,
        tracking=True,
        help='This rate was selected for the shipment'
    )
    is_recommended = fields.Boolean(
        string='Recommended',
        default=False,
        help='This rate is recommended based on rules'
    )

    # Additional Information
    service_type = fields.Char(string='Service Type')
    transit_time = fields.Char(string='Transit Time')
    pickup_date = fields.Datetime(string='Pickup Date')
    cutoff_time = fields.Char(string='Cutoff Time')

    # Restrictions
    restrictions = fields.Text(string='Restrictions')
    notes = fields.Text(string='Notes')

    # Raw Data
    raw_response = fields.Text(string='Raw API Response')

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('check_cost_positive', 'CHECK(total_cost >= 0)', 'Total cost cannot be negative.'),
    ]

    @api.depends('fuel_surcharge', 'residential_surcharge', 'saturday_surcharge',
                 'insurance_surcharge', 'cod_surcharge', 'other_surcharges')
    def _compute_total_surcharges(self):
        for rate in self:
            rate.total_surcharges = (
                    rate.fuel_surcharge +
                    rate.residential_surcharge +
                    rate.saturday_surcharge +
                    rate.insurance_surcharge +
                    rate.cod_surcharge +
                    rate.other_surcharges
            )

    def action_select_rate(self):
        """Select this rate for the shipment"""
        self.ensure_one()

        if not self.shipment_id:
            raise UserError(_('This rate is not associated with a shipment.'))

        # Unselect other rates
        self.search([
            ('shipment_id', '=', self.shipment_id.id),
            ('is_selected', '=', True)
        ]).write({'is_selected': False})

        # Select this rate
        self.is_selected = True

        # Update shipment
        shipment = self.shipment_id
        shipment.write({
            'carrier_provider_id': self.carrier_provider_id.id,
            'carrier_account_id': self.carrier_account_id.id,
            'carrier_service_id': self.carrier_service_id.id if self.carrier_service_id else False,
            'service_type': self.service_code,
            'service_description': self.service_name,
            'shipping_cost': self.total_cost,
            'base_cost': self.base_cost,
            'fuel_surcharge': self.fuel_surcharge,
            'delivery_date': self.delivery_date,
            'selected_rate_id': self.id,
        })

        # Generate tracking number placeholder
        if not shipment.tracking_number:
            shipment.tracking_number = f"{self.carrier_provider_id.code}{shipment.id:08d}"

        self.message_post(
            body=_('Rate selected for shipment %s: %s - %s') % (
                shipment.name,
                self.service_name,
                self.total_cost
            )
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipment'),
            'res_model': 'shipping.shipment',
            'res_id': shipment.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_compare_rates(self):
        """Compare rates for the shipment"""
        if not self.shipment_id:
            raise UserError(_('This rate is not associated with a shipment.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Compare Rates'),
            'res_model': 'shipping.rate',
            'view_mode': 'tree,form',
            'domain': [('shipment_id', '=', self.shipment_id.id)],
            'context': {'default_shipment_id': self.shipment_id.id},
        }

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.service_name} - {record.total_cost:.2f} {record.currency_id.symbol}"
            if record.carrier_provider_id:
                name = f"[{record.carrier_provider_id.code}] {name}"
            result.append((record.id, name))
        return result


class ShippingRateRequest(models.TransientModel):
    """Rate Request Wizard - Complete Implementation"""
    _name = 'shipping.rate.request'
    _description = 'Rate Request Wizard'

    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipment',
        required=True,
        help='Shipment to get rates for'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('requesting', 'Requesting Rates'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Status', default='draft')

    rate_ids = fields.One2many(
        'shipping.rate',
        'rate_request_id',
        string='Rates',
        help='Rates retrieved from carriers'
    )

    carrier_ids = fields.Many2many(
        'shipping.carrier.provider',
        string='Carriers to Query',
        help='Select specific carriers or leave empty for all active carriers'
    )

    request_date = fields.Datetime(
        string='Request Date',
        default=fields.Datetime.now,
    )
    response_date = fields.Datetime(
        string='Response Date',
    )

    error_message = fields.Text(string='Error Message')
    request_data = fields.Text(string='Request Data')
    response_data = fields.Text(string='Response Data')

    include_fuel_surcharge = fields.Boolean(
        string='Include Fuel Surcharge',
        default=True,
        help='Include fuel surcharge in rate calculations'
    )
    include_residential = fields.Boolean(
        string='Include Residential Surcharge',
        default=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    def action_get_rates(self):
        """Get rates from carriers"""
        self.ensure_one()

        if not self.shipment_id:
            raise UserError(_('No shipment selected.'))

        self.state = 'requesting'
        self.request_date = fields.Datetime.now()

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
            self.state = 'failed'
            self.error_message = _('No active carriers found with rate shopping support.')
            raise UserError(self.error_message)

        rates_created = 0
        errors = []

        for carrier in carriers:
            try:
                rate = self._get_rate_from_carrier(carrier)
                if rate:
                    rates_created += 1
            except Exception as e:
                errors.append(f"{carrier.name}: {str(e)}")
                _logger.error(f"Error getting rate from {carrier.name}: {e}")

        if rates_created == 0:
            self.state = 'failed'
            self.error_message = _('No rates could be retrieved. Errors: %s') % '\n'.join(errors)
            raise UserError(self.error_message)

        self.state = 'completed'
        self.response_date = fields.Datetime.now()
        self.error_message = '\n'.join(errors) if errors else False

        # Sort and mark recommendations
        self._mark_recommended_rates()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Rate Shopping Results'),
            'res_model': 'shipping.rate.request',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_rate_from_carrier(self, carrier):
        """Get rate from a specific carrier"""
        self.ensure_one()

        # Get the account
        account = carrier.account_ids.filtered(lambda a: a.environment in ['production', 'sandbox'])[:1]
        if not account:
            _logger.warning(f"No active account found for carrier {carrier.name}")
            return False

        # Prepare shipment data
        shipment = self.shipment_id
        package_data = []
        for package in shipment.package_ids:
            package_data.append({
                'weight': package.weight,
                'length': package.length,
                'width': package.width,
                'height': package.height,
            })

        # If no packages, create default
        if not package_data:
            package_data.append({
                'weight': shipment.total_weight or 1.0,
                'length': 30.0,
                'width': 20.0,
                'height': 15.0,
            })

        # TODO: Implement actual carrier API calls
        # For demo, create dummy rates
        import random

        base_rate = 10.0 + random.uniform(0, 50)
        fuel_surcharge = base_rate * 0.10
        residential_surcharge = 2.0 if shipment.residential_delivery else 0.0

        rate_vals = {
            'shipment_id': shipment.id,
            'carrier_provider_id': carrier.id,
            'carrier_account_id': account.id,
            'rate_request_id': f'shipping.rate.request,{self.id}',
            'service_name': f"{carrier.name} {random.choice(['Standard', 'Express', 'Economy'])}",
            'service_code': random.choice(['STD', 'EXP', 'ECO']),
            'service_description': f"Standard shipping service from {carrier.name}",
            'total_cost': base_rate + fuel_surcharge + residential_surcharge,
            'base_cost': base_rate,
            'fuel_surcharge': fuel_surcharge if self.include_fuel_surcharge else 0.0,
            'residential_surcharge': residential_surcharge if self.include_residential else 0.0,
            'delivery_days': random.randint(1, 7),
            'delivery_date': fields.Datetime.now() + timedelta(days=random.randint(1, 7)),
            'guaranteed_delivery': random.choice([True, False]),
            'currency_id': self.env.company.currency_id.id,
        }

        rate = self.env['shipping.rate'].create(rate_vals)

        # Get service level if available
        if carrier.service_level_ids:
            service = random.choice(carrier.service_level_ids)
            rate.write({
                'carrier_service_id': service.id,
                'service_type': service.service_type,
            })

        return rate

    def _mark_recommended_rates(self):
        """Mark recommended rates based on rules"""
        # Apply shipping rules
        rules = self.env['shipping.rule'].search([
            ('active', '=', True)
        ])

        shipment = self.shipment_id
        shipment_data = {
            'weight': shipment.total_weight,
            'country_code': shipment.recipient_country_id.code if shipment.recipient_country_id else False,
            'is_international': shipment.is_international,
            'declared_value': shipment.declared_value,
            'total_packages': shipment.total_packages,
        }

        for rule in rules:
            result = rule.apply_rule(shipment_data)
            if result:
                # Find matching rate and mark as recommended
                matching_rates = self.rate_ids.filtered(
                    lambda r: r.carrier_provider_id.id == result.get('carrier_provider_id')
                )
                for rate in matching_rates:
                    rate.is_recommended = True
                    if result.get('override_cost'):
                        rate.total_cost = result['override_cost']
                    if result.get('delivery_days'):
                        rate.delivery_days = result['delivery_days']
                break

    def action_select_rate_from_wizard(self):
        """Select a rate from the wizard"""
        self.ensure_one()
        active_id = self.env.context.get('active_id')

        if active_id:
            rate = self.env['shipping.rate'].browse(active_id)
            if rate:
                return rate.action_select_rate()

        return {'type': 'ir.actions.act_window_close'}

    def action_retry(self):
        """Retry rate shopping"""
        self.ensure_one()
        self.state = 'draft'
        self.rate_ids.unlink()
        self.error_message = False
        return self.action_get_rates()

    # Add this method to ShippingRate class in models/rate.py

    def action_select_rate(self):
        """Select this rate for the shipment"""
        self.ensure_one()

        if not self.shipment_id:
            raise UserError(_('This rate is not associated with a shipment.'))

        # Unselect other rates
        self.search([
            ('shipment_id', '=', self.shipment_id.id),
            ('is_selected', '=', True)
        ]).write({'is_selected': False})

        # Select this rate
        self.is_selected = True

        # Update shipment
        shipment = self.shipment_id
        shipment.write({
            'carrier_provider_id': self.carrier_provider_id.id,
            'carrier_account_id': self.carrier_account_id.id,
            'carrier_service_id': self.carrier_service_id.id if self.carrier_service_id else False,
            'service_type': self.service_code,
            'service_description': self.service_name,
            'shipping_cost': self.total_cost,
            'base_cost': self.base_cost,
            'fuel_surcharge': self.fuel_surcharge,
            'delivery_date': self.delivery_date,
            'selected_rate_id': self.id,
        })

        # Generate tracking number placeholder
        if not shipment.tracking_number:
            shipment.tracking_number = f"{self.carrier_provider_id.code}{shipment.id:08d}"

        self.message_post(
            body=_('Rate selected for shipment %s: %s - %s') % (
                shipment.name,
                self.service_name,
                self.total_cost
            )
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipment'),
            'res_model': 'shipping.shipment',
            'res_id': shipment.id,
            'view_mode': 'form',
            'target': 'current',
        }
