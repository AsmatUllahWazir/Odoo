from odoo import fields, http, _
from odoo.http import request


class DeliveryTrackingController(http.Controller):
    @http.route("/delivery/track/<string:token>", type="http", auth="public", website=False, sitemap=False)
    def delivery_tracking(self, token, **kwargs):
        link = request.env["delivery.tracking.link"].sudo().search([("token", "=", token)], limit=1)
        if not link or not link.active or (link.expires_at and link.expires_at < fields.Datetime.now()):
            return request.not_found()
        try:
            link.register_access()
        except Exception:
            return request.not_found()
        line = link.route_line_id
        events = request.env["delivery.event"].sudo().search(
            [("route_line_id", "=", line.id), ("is_customer_visible", "=", True)], order="event_datetime desc"
        )
        values = {
            "line": line,
            "route": line.route_id,
            "partner": line.partner_id,
            "events": events,
            "token": token,
        }
        return request.render("delivery_fleet_pro.delivery_tracking_page", values)

    @http.route("/delivery/track/<string:token>/json", type="json", auth="public", methods=["POST"], csrf=False)
    def delivery_tracking_json(self, token, **kwargs):
        link = request.env["delivery.tracking.link"].sudo().search([("token", "=", token)], limit=1)
        if not link or not link.active or (link.expires_at and link.expires_at < fields.Datetime.now()):
            return {"error": _("Invalid or expired tracking link.")}
        line = link.route_line_id
        return {
            "route": line.route_id.name,
            "status": line.status,
            "status_label": dict(line._fields["status"].selection).get(line.status, line.status),
            "customer": line.partner_id.name,
            "address": line.address,
            "latitude": line.latitude,
            "longitude": line.longitude,
            "updated_at": line.write_date.isoformat() if line.write_date else None,
            "delivered_count": line.route_id.delivered_count,
            "stop_count": line.route_id.stop_count,
        }

try:
    from odoo.addons.portal.controllers.portal import CustomerPortal
except ImportError:
    CustomerPortal = http.Controller


class DeliveryPortalController(CustomerPortal):
    @http.route(["/my/deliveries"], type="http", auth="user", website=True)
    def portal_deliveries(self, **kwargs):
        partner = request.env.user.partner_id.commercial_partner_id
        links = request.env["delivery.tracking.link"].sudo().search(
            [("partner_id", "child_of", partner.id), ("active", "=", True)],
            order="create_date desc",
        )
        lines = links.mapped("route_line_id")
        values = {
            "links": links,
            "partner": partner,
            "page_name": "delivery",
            "delivered_count": len(lines.filtered(lambda line: line.status == "delivered")),
            "active_count": len(lines.filtered(lambda line: line.status in ("assigned", "in_transit", "arrived", "pending"))),
            "failed_count": len(lines.filtered(lambda line: line.status in ("failed", "retry"))),
        }
        return request.render("delivery_fleet_pro.portal_my_deliveries", values)

    @http.route(["/my/deliveries/<int:line_id>"], type="http", auth="user", website=True)
    def portal_delivery_detail(self, line_id, **kwargs):
        partner = request.env.user.partner_id.commercial_partner_id
        line = request.env["delivery.route.line"].sudo().browse(line_id).exists()
        if not line or line.partner_id.commercial_partner_id != partner:
            return request.not_found()
        events = request.env["delivery.event"].sudo().search(
            [("route_line_id", "=", line.id), ("is_customer_visible", "=", True)], order="event_datetime desc"
        )
        return request.render(
            "delivery_fleet_pro.portal_delivery_detail",
            {"line": line, "route": line.route_id, "events": events, "page_name": "delivery"},
        )
