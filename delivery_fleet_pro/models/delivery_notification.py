from odoo import api, fields, models, _


class DeliveryNotification(models.Model):
    _name = "delivery.notification"
    _description = "Delivery Notification Log"
    _order = "sent_at desc, id desc"

    name = fields.Char(required=True)
    route_id = fields.Many2one("delivery.route", ondelete="set null")
    route_line_id = fields.Many2one("delivery.route.line", ondelete="set null")
    partner_id = fields.Many2one("res.partner")
    notification_type = fields.Selection(
        [("planned", "Planned"), ("dispatched", "Dispatched"), ("in_transit", "In Transit"), ("arriving", "Arriving"), ("delivered", "Delivered"), ("failed", "Failed"), ("retry", "Retry")],
        required=True,
    )
    channel = fields.Selection(
        [("email", "Email"), ("sms", "SMS"), ("portal", "Portal"), ("push", "Push")],
        required=True,
        default="email",
    )
    recipient = fields.Char()
    subject = fields.Char()
    body = fields.Text()
    sent_at = fields.Datetime()
    state = fields.Selection(
        [("pending", "Pending"), ("sent", "Sent"), ("failed", "Failed"), ("cancelled", "Cancelled")],
        default="pending",
        required=True,
    )
    error_message = fields.Text()
    retry_count = fields.Integer(default=0)

    def mark_sent(self):
        self.write({"state": "sent", "sent_at": fields.Datetime.now()})

    def mark_failed(self, message):
        self.write({"state": "failed", "error_message": message, "retry_count": self.mapped("retry_count")[0] + 1 if self else 0})

    @api.model
    def log(self, line, notification_type, channel="email", subject=False, body=False, recipient=False):
        return self.create({
            "name": _("%s - %s") % (line.display_name, notification_type),
            "route_id": line.route_id.id,
            "route_line_id": line.id,
            "partner_id": line.partner_id.id,
            "notification_type": notification_type,
            "channel": channel,
            "recipient": recipient or line.partner_id.email,
            "subject": subject,
            "body": body,
        })
