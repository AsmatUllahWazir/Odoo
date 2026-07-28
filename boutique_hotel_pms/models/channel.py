from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class HotelChannel(models.Model):
    _name = 'hotel.channel'
    _description = 'Hotel Channel'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Channel Name',
        required=True,
        translate=True,
        help='Name of the channel (e.g., Booking.com, Expedia, Agoda)'
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Short code for the channel'
    )
    channel_type = fields.Selection([
        ('ota', 'OTA - Online Travel Agency'),
        ('gds', 'GDS - Global Distribution System'),
        ('direct', 'Direct Booking'),
        ('corporate', 'Corporate'),
        ('travel_agent', 'Travel Agent'),
        ('wholesale', 'Wholesale'),
        ('other', 'Other')
    ], string='Channel Type', required=True,
        help='Type of channel')
    website = fields.Char(
        string='Website',
        help='Channel website URL'
    )
    api_url = fields.Char(
        string='API URL',
        help='API endpoint for integration'
    )
    api_key = fields.Char(
        string='API Key',
        help='API key for authentication'
    )
    commission_rate = fields.Float(
        string='Commission Rate (%)',
        help='Commission rate charged by this channel'
    )
    commission_model = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('per_booking', 'Per Booking')
    ], string='Commission Model', default='percentage',
        help='How commission is calculated')
    commission_amount = fields.Monetary(
        string='Commission Amount',
        currency_field='currency_id',
        help='Fixed commission amount if applicable'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    # Channel Settings
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this channel is active'
    )
    auto_confirm = fields.Boolean(
        string='Auto Confirm',
        default=False,
        help='Whether to auto-confirm reservations from this channel'
    )
    auto_create_guest = fields.Boolean(
        string='Auto Create Guest',
        default=True,
        help='Whether to auto-create guest records'
    )
    auto_send_confirmation = fields.Boolean(
        string='Auto Send Confirmation',
        default=True,
        help='Whether to auto-send confirmation emails'
    )
    inventory_sync = fields.Boolean(
        string='Inventory Sync',
        default=False,
        help='Whether to sync inventory with this channel'
    )
    last_sync_date = fields.Datetime(
        string='Last Sync Date',
        help='Date of last synchronization'
    )
    sync_status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress')
    ], string='Sync Status',
        help='Current sync status')

    # Additional Fields
    description = fields.Text(
        string='Description',
        help='Description of the channel'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.constrains('commission_rate')
    def _check_commission(self):
        for record in self:
            if record.commission_rate and record.commission_rate < 0:
                raise ValidationError('Commission rate cannot be negative.')

    @api.constrains('commission_amount')
    def _check_commission_amount(self):
        for record in self:
            if record.commission_amount and record.commission_amount < 0:
                raise ValidationError('Commission amount cannot be negative.')

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.code} - {record.name}"
            if record.channel_type:
                name += f" ({dict(self._fields['channel_type'].selection).get(record.channel_type)})"
            result.append((record.id, name))
        return result

    def action_sync_inventory(self):
        self.ensure_one()
        self.sync_status = 'in_progress'
        try:
            # Simulate sync
            self.last_sync_date = fields.Datetime.now()
            self.sync_status = 'success'
            self.message_post(body=_('Inventory sync completed successfully.'))
        except Exception as e:
            self.sync_status = 'failed'
            self.message_post(body=_('Inventory sync failed: %s') % str(e))
        return True

    def action_view_reservations(self):
        self.ensure_one()
        return {
            'name': _('Channel Reservations'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reservation',
            'view_mode': 'tree,form',
            'domain': [('source_channel_id', '=', self.id)],
            'target': 'current',
        }
    