from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ShippingNotification(models.Model):
    """Shipping Notifications"""
    _name = 'shipping.notification'
    _description = 'Shipping Notification'
    _order = 'create_date desc'
    _rec_name = 'subject'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    subject = fields.Char(string='Subject', required=True, tracking=True)
    body = fields.Html(string='Body', required=True)

    notification_type = fields.Selection([
        ('label_generated', 'Label Generated'),
        ('tracking_update', 'Tracking Update'),
        ('delivery_confirmation', 'Delivery Confirmation'),
        ('exception', 'Exception'),
        ('return_approved', 'Return Approved'),
        ('return_received', 'Return Received'),
        ('shipment_created', 'Shipment Created'),
        ('rate_available', 'Rates Available'),
        ('custom', 'Custom'),
    ], string='Notification Type', required=True, default='custom')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ], string='Status', default='draft', tracking=True)

    # Related Records
    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Related Shipment',
    )
    return_id = fields.Many2one(
        'shipping.return',
        string='Related Return',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Recipient',
        required=True,
    )

    # Delivery Methods
    delivery_method = fields.Selection([
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('portal', 'Portal'),
        ('slack', 'Slack'),
        ('webhook', 'Webhook'),
    ], string='Delivery Method', default='email', required=True)

    email_to = fields.Char(string='Email To')
    phone_to = fields.Char(string='Phone Number')

    # Email Template
    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
    )

    # Delivery Status
    sent_date = fields.Datetime(string='Sent Date')
    read_date = fields.Datetime(string='Read Date')
    delivery_error = fields.Text(string='Delivery Error')

    # Priority
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.model
    def send_notification(self, vals):
        """Send a notification"""
        notification = self.create(vals)
        notification.action_send()
        return notification

    def action_send(self):
        """Send the notification"""
        self.ensure_one()
        try:
            if self.delivery_method == 'email' and self.email_to:
                # Send email
                template = self.email_template_id
                if template:
                    template.send_mail(self.id, force_send=True)
                else:
                    # Send simple email
                    mail = self.env['mail.mail'].create({
                        'subject': self.subject,
                        'body_html': self.body,
                        'email_to': self.email_to,
                    })
                    mail.send()

            self.state = 'sent'
            self.sent_date = fields.Datetime.now()

        except Exception as e:
            self.state = 'failed'
            self.delivery_error = str(e)
            _logger.error(f"Failed to send notification: {e}")
            raise UserError(_('Failed to send notification: %s') % str(e))

    def action_mark_read(self):
        """Mark notification as read"""
        self.ensure_one()
        self.state = 'read'
        self.read_date = fields.Datetime.now()
