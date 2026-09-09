import secrets
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryTrackingLink(models.Model):
    _name = "delivery.tracking.link"
    _description = "Customer Delivery Tracking Link"
    _order = "create_date desc"

    name = fields.Char(required=True, copy=False)
    token = fields.Char(required=True, copy=False, index=True)
    route_id = fields.Many2one("delivery.route", ondelete="cascade")
    route_line_id = fields.Many2one("delivery.route.line", ondelete="cascade")
    partner_id = fields.Many2one("res.partner", related="route_line_id.partner_id", store=True)
    expires_at = fields.Datetime()
    active = fields.Boolean(default=True)
    last_access = fields.Datetime()
    access_count = fields.Integer(default=0)

    _sql_constraints = [("token_unique", "unique(token)", "Tracking token must be unique.")]

    @api.model
    def create_for_line(self, line, expires_at=None):
        self.search([("route_line_id", "=", line.id), ("active", "=", True)]).write({"active": False})
        token = secrets.token_urlsafe(24)
        return self.create(
            {
                "name": _("Tracking - %s") % line.display_name,
                "token": token,
                "route_id": line.route_id.id,
                "route_line_id": line.id,
                "expires_at": expires_at or fields.Datetime.now() + timedelta(days=30),
            }
        )

    def register_access(self):
        self.ensure_one()
        if not self.active or (self.expires_at and self.expires_at < fields.Datetime.now()):
            raise UserError(_("This tracking link has expired."))
        self.write({"last_access": fields.Datetime.now(), "access_count": self.access_count + 1})
