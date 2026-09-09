from odoo import api, fields, models, _


class DeliveryNotificationService(models.AbstractModel):
    _name = "delivery.notification.service"
    _description = "Delivery Notification Service"

    @api.model
    def send_line_status(self, line, status, force=False):
        config = self.env["delivery.config"].sudo().get_company_config(line.route_id.company_id)
        if not config.customer_notifications and not force:
            return False
        partner = line.partner_id
        if not partner or not partner.email:
            return False
        subject = _("Delivery update for %s") % (partner.name or _("Customer"))
        body = self._build_status_body(line, status)
        mail = self.env["mail.mail"].sudo().create({
            "subject": subject,
            "body_html": body,
            "email_to": partner.email,
            "author_id": self.env.user.partner_id.id,
        })
        mail.send()
        self.env["delivery.notification"].sudo().create({
            "name": "%s - %s" % (line.display_name, status),
            "route_id": line.route_id.id,
            "route_line_id": line.id,
            "partner_id": partner.id,
            "notification_type": status if status in dict(self.env["delivery.notification"]._fields["notification_type"].selection) else "portal",
            "channel": "email",
            "recipient": partner.email,
            "subject": subject,
            "body": body,
            "state": "sent",
            "sent_at": fields.Datetime.now(),
        })
        return True

    @api.model
    def _build_status_body(self, line, status):
        label = dict(line._fields["status"].selection).get(status, status)
        return """<div style=\"font-family:Arial,sans-serif;max-width:650px;margin:auto;\">\n            <div style=\"background:#17324d;color:#fff;padding:22px;border-radius:12px;\">\n                <div style=\"font-size:11px;letter-spacing:1px;opacity:.8;\">DELIVERY FLEET PRO</div>\n                <h2 style=\"margin:7px 0 0;\">Delivery status update</h2>\n            </div>\n            <div style=\"padding:20px;border:1px solid #e5eaf0;margin-top:12px;border-radius:12px;\">\n                <p>Hello <strong>%s</strong>,</p>\n                <p>Your delivery <strong>%s</strong> is now <strong>%s</strong>.</p>\n                <p style=\"color:#6c7a89;\">Address: %s</p>\n            </div>\n        </div>""" % (line.partner_id.name or "", line.picking_id.name or line.display_name, label, line.address or "")

    @api.model
    def notify_route(self, route, status):
        sent = 0
        for line in route.line_ids.filtered(lambda item: item.partner_id and item.partner_id.email):
            if self.send_line_status(line, status):
                sent += 1
        return sent

    @api.model
    def notify_arriving(self, line):
        return self.send_line_status(line, "arriving")
