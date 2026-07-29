from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ShippingCarrierAccount(models.Model):
    """Carrier Account Configuration"""
    _name = 'shipping.carrier.account'
    _description = 'Shipping Carrier Account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'provider_id, name'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Account Name',
        required=True,
        tracking=True,
        translate=True,
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )

    provider_id = fields.Many2one(
        'shipping.carrier.provider',
        string='Carrier Provider',
        required=True,
        tracking=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
    )
    is_default = fields.Boolean(
        string='Default Account',
        default=False,
        help='Mark as default account for this carrier'
    )

    # API Credentials
    api_key = fields.Char(string='API Key', tracking=True)
    api_secret = fields.Char(string='API Secret', tracking=True)
    username = fields.Char(string='Username', tracking=True)
    password = fields.Char(string='Password', tracking=True)
    account_number = fields.Char(string='Account Number', tracking=True)
    meter_number = fields.Char(string='Meter Number')
    license_number = fields.Char(string='License Number')

    # Environment
    environment = fields.Selection([
        ('sandbox', 'Sandbox/Test'),
        ('development', 'Development'),
        ('staging', 'Staging'),
        ('production', 'Production'),
    ], string='Environment', default='sandbox', required=True, tracking=True)

    # API URLs
    test_api_url = fields.Char(string='Test/Sandbox API URL')
    production_api_url = fields.Char(string='Production API URL')
    test_api_key = fields.Char(string='Test API Key')
    test_api_secret = fields.Char(string='Test API Secret')

    # Authentication
    auth_type = fields.Selection([
        ('api_key', 'API Key'),
        ('oauth2', 'OAuth2'),
        ('basic', 'Basic Auth'),
        ('digest', 'Digest Auth'),
        ('jwt', 'JWT Token'),
    ], string='Authentication Type', default='api_key')

    oauth2_client_id = fields.Char(string='OAuth2 Client ID')
    oauth2_client_secret = fields.Char(string='OAuth2 Client Secret')
    oauth2_token_url = fields.Char(string='OAuth2 Token URL')
    oauth2_refresh_token = fields.Char(string='OAuth2 Refresh Token')

    # Default Settings
    default_weight_uom = fields.Selection([
        ('kg', 'Kilograms'),
        ('lb', 'Pounds'),
        ('oz', 'Ounces'),
        ('g', 'Grams'),
    ], string='Default Weight UoM', default='kg')

    default_dimension_uom = fields.Selection([
        ('cm', 'Centimeters'),
        ('in', 'Inches'),
        ('m', 'Meters'),
        ('ft', 'Feet'),
    ], string='Default Dimension UoM', default='cm')

    default_package_type = fields.Selection([
        ('box', 'Box'),
        ('envelope', 'Envelope'),
        ('pallet', 'Pallet'),
        ('tube', 'Tube'),
        ('custom', 'Custom'),
    ], string='Default Package Type', default='box')

    default_service_level = fields.Many2one(
        'shipping.carrier.service',
        string='Default Service Level',
        domain="[('provider_id', '=', provider_id)]"
    )

    # Shipping Options
    default_signature_required = fields.Boolean(string='Default Signature Required')
    default_saturday_delivery = fields.Boolean(string='Default Saturday Delivery')
    default_residential = fields.Boolean(string='Default Residential Delivery')
    default_insurance = fields.Boolean(string='Default Insurance')

    # Rate Limits
    requests_per_minute = fields.Integer(string='Max Requests/Minute', default=60)
    requests_per_hour = fields.Integer(string='Max Requests/Hour', default=1000)
    requests_per_day = fields.Integer(string='Max Requests/Day', default=10000)
    current_requests = fields.Integer(string='Current Requests Count', default=0)
    last_reset_date = fields.Datetime(string='Last Reset Date')

    # Usage Statistics
    last_used_date = fields.Datetime(string='Last Used Date')
    total_requests = fields.Integer(string='Total API Requests', default=0)
    success_requests = fields.Integer(string='Successful Requests', default=0)
    failed_requests = fields.Integer(string='Failed Requests', default=0)
    last_error = fields.Text(string='Last Error')

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # Custom Fields
    custom_fields = fields.Text(string='Custom Fields (JSON)')

    _sql_constraints = [
        ('unique_provider_account', 'unique(provider_id, name)',
         'Account name must be unique per carrier provider!'),
        ('unique_default', 'unique(provider_id, is_default)',
         'Only one default account allowed per carrier!'),
    ]

    @api.depends('name', 'provider_id')
    def _compute_display_name(self):
        for record in self:
            provider_name = record.provider_id.name if record.provider_id else ''
            env_label = f"({record.environment})" if record.environment else ''
            record.display_name = f"{record.name} {env_label} - {provider_name}"

    @api.constrains('environment', 'api_key', 'api_secret')
    def _check_environment_credentials(self):
        for record in self:
            if record.environment == 'production' and not record.api_key:
                raise ValidationError(_('API Key is required for production environment.'))
            if record.environment == 'production' and not record.api_secret:
                raise ValidationError(_('API Secret is required for production environment.'))

    @api.onchange('provider_id')
    def _onchange_provider_id(self):
        if self.provider_id:
            self.company_id = self.provider_id.company_id.id

    def action_reset_counters(self):
        """Reset request counters"""
        self.ensure_one()
        self.current_requests = 0
        self.last_reset_date = fields.Datetime.now()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Counters Reset'),
                'message': _('Request counters have been reset successfully.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_test_connection(self):
        """Test API connection with this account"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connection Test'),
                'message': _('Connection test initiated for %s.') % self.display_name,
                'type': 'info',
                'sticky': False,
            }
        }

    def action_view_shipments(self):
        """View shipments using this account"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipments for %s') % self.display_name,
            'res_model': 'shipping.shipment',
            'view_mode': 'tree,form',
            'domain': [('carrier_account_id', '=', self.id)],
        }

    @api.model
    def increment_request_count(self, account_id, success=True):
        """Increment request counter for an account"""
        account = self.browse(account_id)
        if account:
            now = fields.Datetime.now()
            if not account.last_reset_date or (now - account.last_reset_date).days > 0:
                account.current_requests = 0
                account.last_reset_date = now

            account.current_requests += 1
            account.total_requests += 1
            if success:
                account.success_requests += 1
            else:
                account.failed_requests += 1
            account.last_used_date = now

    @api.model
    def check_rate_limit(self, account_id):
        """Check if rate limit is exceeded"""
        account = self.browse(account_id)
        if account:
            if account.current_requests >= account.requests_per_minute:
                raise ValidationError(_('Rate limit exceeded for account %s. Please try again later.') % account.name)
            return True
        return False
