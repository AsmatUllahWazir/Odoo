from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class ShippingConfig(models.Model):
    """Global Shipping Configuration"""
    _name = 'shipping.config'
    _description = 'Shipping Configuration'
    _rec_name = 'company_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    # General Settings
    default_shipper_name = fields.Char(string='Default Shipper Name')
    default_shipper_address = fields.Text(string='Default Shipper Address')
    default_shipper_phone = fields.Char(string='Default Shipper Phone')
    default_shipper_email = fields.Char(string='Default Shipper Email')

    # Default Carrier
    default_carrier_provider_id = fields.Many2one(
        'shipping.carrier.provider',
        string='Default Carrier Provider',
    )
    default_carrier_account_id = fields.Many2one(
        'shipping.carrier.account',
        string='Default Carrier Account',
        domain="[('provider_id', '=', default_carrier_provider_id)]"
    )

    # Shipping Defaults
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

    # Notification Settings
    notify_on_label_generation = fields.Boolean(
        string='Notify on Label Generation',
        default=True,
        help='Send notification when shipping label is generated'
    )
    notify_on_tracking_update = fields.Boolean(
        string='Notify on Tracking Update',
        default=True,
        help='Send notification when tracking is updated'
    )
    notify_on_delivery = fields.Boolean(
        string='Notify on Delivery',
        default=True,
        help='Send notification when shipment is delivered'
    )
    notify_on_exception = fields.Boolean(
        string='Notify on Exception',
        default=True,
        help='Send notification when shipment has exceptions'
    )

    # Email Settings
    email_template_shipment_confirmation = fields.Many2one(
        'mail.template',
        string='Shipment Confirmation Email',
        domain="[('model', '=', 'shipping.shipment')]"
    )
    email_template_shipment_delivered = fields.Many2one(
        'mail.template',
        string='Shipment Delivered Email',
        domain="[('model', '=', 'shipping.shipment')]"
    )
    email_template_tracking_updated = fields.Many2one(
        'mail.template',
        string='Tracking Updated Email',
        domain="[('model', '=', 'shipping.shipment')]"
    )
    email_template_return_approved = fields.Many2one(
        'mail.template',
        string='Return Approved Email',
        domain="[('model', '=', 'shipping.return')]"
    )

    # Barcode Settings
    barcode_type = fields.Selection([
        ('code128', 'Code 128'),
        ('code39', 'Code 39'),
        ('qr', 'QR Code'),
        ('datamatrix', 'Data Matrix'),
        ('pdf417', 'PDF417'),
    ], string='Barcode Type', default='code128')

    include_barcode_in_label = fields.Boolean(
        string='Include Barcode in Label',
        default=True,
    )

    # Label Settings
    label_format = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('png', 'PNG'),
        ('jpeg', 'JPEG'),
    ], string='Label Format', default='pdf')

    label_page_size = fields.Selection([
        ('a4', 'A4'),
        ('letter', 'Letter'),
        ('label_4x6', '4x6 Label'),
        ('label_4x8', '4x8 Label'),
    ], string='Label Page Size', default='label_4x6')

    # Tracking Settings
    auto_update_tracking = fields.Boolean(
        string='Auto-Update Tracking',
        default=True,
        help='Automatically update tracking via cron job'
    )
    tracking_update_interval = fields.Integer(
        string='Tracking Update Interval (minutes)',
        default=30,
        help='How often to check for tracking updates'
    )
    max_tracking_retries = fields.Integer(
        string='Max Tracking Retries',
        default=5,
        help='Maximum number of retries for tracking updates'
    )

    # Rate Shopping Settings
    rate_shopping_timeout = fields.Integer(
        string='Rate Shopping Timeout (seconds)',
        default=30,
        help='Timeout for rate shopping API calls'
    )
    max_rates_to_show = fields.Integer(
        string='Maximum Rates to Show',
        default=10,
        help='Maximum number of rates to display in comparison'
    )

    # Return Settings
    return_window_days = fields.Integer(
        string='Return Window (Days)',
        default=30,
        help='Number of days customers have to return items'
    )
    restocking_fee_percent = fields.Float(
        string='Restocking Fee %',
        default=0.0,
        help='Default restocking fee percentage'
    )

    # Insurance Settings
    default_insurance_amount = fields.Monetary(
        string='Default Insurance Amount',
        currency_field='currency_id',
    )
    insurance_rate_percent = fields.Float(
        string='Insurance Rate %',
        default=1.0,
        help='Percentage of declared value for insurance cost'
    )

    # COD Settings
    cod_fee = fields.Monetary(
        string='COD Fee',
        currency_field='currency_id',
        default=5.0,
        help='Default COD handling fee'
    )
    cod_percent = fields.Float(
        string='COD Percentage',
        default=2.0,
        help='Percentage of COD amount as fee'
    )

    # Integration Settings
    enable_webhooks = fields.Boolean(
        string='Enable Webhooks',
        default=False,
    )
    webhook_secret = fields.Char(
        string='Webhook Secret',
        readonly=True,
    )
    webhook_urls = fields.Text(
        string='Webhook URLs',
        help='Comma-separated list of webhook URLs',
    )

    # API Logging
    enable_api_logging = fields.Boolean(
        string='Enable API Logging',
        default=True,
        help='Log all API requests and responses for debugging'
    )
    api_log_retention_days = fields.Integer(
        string='API Log Retention (Days)',
        default=30,
        help='Number of days to keep API logs'
    )

    # Performance
    enable_caching = fields.Boolean(
        string='Enable Caching',
        default=True,
        help='Cache rate shopping and tracking results'
    )
    cache_timeout_minutes = fields.Integer(
        string='Cache Timeout (Minutes)',
        default=60,
        help='How long to cache results'
    )

    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    _sql_constraints = [
        ('unique_company', 'unique(company_id)', 'Only one configuration per company allowed!'),
    ]

    @api.model
    def _get_default_config(self):
        """Get the default shipping configuration"""
        return self.search([('company_id', '=', self.env.company.id)], limit=1)

    def action_generate_webhook_secret(self):
        """Generate new webhook secret"""
        self.ensure_one()
        import secrets
        self.webhook_secret = secrets.token_hex(32)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Webhook Secret Generated'),
                'message': _('New webhook secret has been generated.'),
                'type': 'success',
                'sticky': False,
            }
        }
    