from odoo import fields, http, _
from odoo.http import request


class DeliveryDriverAPI(http.Controller):
    """Small authenticated JSON API used by a future mobile/driver web client.

    The API deliberately uses Odoo's session authentication rather than exposing
    internal model identifiers to anonymous callers. Every endpoint verifies that
    the current user owns an employee record and that the requested route belongs
    to that employee.
    """

    def _employee(self):
        employee = request.env["hr.employee"].sudo().search([("user_id", "=", request.env.user.id)], limit=1)
        if not employee:
            return request.env["hr.employee"]
        return employee

    def _route_for_employee(self, route_id):
        employee = self._employee()
        route = request.env["delivery.route"].sudo().browse(int(route_id)).exists()
        if not employee or not route or route.driver_id != employee:
            return request.env["delivery.route"]
        return route

    def _line_for_employee(self, line_id):
        employee = self._employee()
        line = request.env["delivery.route.line"].sudo().browse(int(line_id)).exists()
        if not employee or not line or line.route_id.driver_id != employee:
            return request.env["delivery.route.line"]
        return line

    def _error(self, message, status=400):
        return request.make_json_response({"ok": False, "error": message}, status=status)

    def _success(self, data=None):
        payload = {"ok": True}
        if data:
            payload.update(data)
        return request.make_json_response(payload)

    def _line_payload(self, line):
        return {
            "id": line.id,
            "sequence": line.sequence,
            "picking": line.picking_id.name,
            "customer": line.partner_id.name,
            "address": line.address,
            "phone": line.phone,
            "latitude": line.latitude,
            "longitude": line.longitude,
            "status": line.status,
            "status_label": dict(line._fields["status"].selection).get(line.status, line.status),
            "date_from": fields.Datetime.to_string(line.date_from) if line.date_from else None,
            "date_to": fields.Datetime.to_string(line.date_to) if line.date_to else None,
            "weight": line.weight,
            "volume": line.volume,
            "package_count": line.package_count,
            "on_time": line.on_time,
            "notes": line.notes or "",
        }

    @http.route("/delivery/api/me", type="http", auth="user", methods=["GET"], csrf=False)
    def me(self, **kwargs):
        employee = self._employee()
        if not employee:
            return self._error(_("No employee is linked to the current user."), 403)
        return self._success({
            "employee_id": employee.id,
            "employee_name": employee.name,
            "available": employee.delivery_available,
            "current_route_id": employee.delivery_current_route_id.id if employee.delivery_current_route_id else None,
        })

    @http.route("/delivery/api/routes", type="http", auth="user", methods=["GET"], csrf=False)
    def routes(self, **kwargs):
        employee = self._employee()
        if not employee:
            return self._error(_("No employee is linked to the current user."), 403)
        routes = request.env["delivery.route"].sudo().search([
            ("driver_id", "=", employee.id),
            ("state", "in", ["planned", "dispatched", "in_transit"]),
        ], order="date, id")
        return self._success({"routes": [self._route_payload(route) for route in routes]})

    def _route_payload(self, route):
        return {
            "id": route.id,
            "name": route.name,
            "date": fields.Date.to_string(route.date),
            "state": route.state,
            "state_label": dict(route._fields["state"].selection).get(route.state, route.state),
            "vehicle_id": route.vehicle_id.id if route.vehicle_id else None,
            "vehicle_name": route.vehicle_id.name if route.vehicle_id else None,
            "stop_count": route.stop_count,
            "delivered_count": route.delivered_count,
            "failed_count": route.failed_count,
            "pending_count": route.pending_count,
            "estimated_distance": route.estimated_distance,
            "estimated_duration": route.estimated_duration,
            "actual_distance": route.actual_distance,
            "actual_duration": route.actual_duration,
            "stops": [self._line_payload(line) for line in route.line_ids.sorted("sequence")],
        }

    @http.route("/delivery/api/routes/<int:route_id>", type="http", auth="user", methods=["GET"], csrf=False)
    def route(self, route_id, **kwargs):
        route = self._route_for_employee(route_id)
        if not route:
            return self._error(_("Route not found."), 404)
        return self._success({"route": self._route_payload(route)})

    @http.route("/delivery/api/routes/<int:route_id>/start", type="http", auth="user", methods=["POST"], csrf=False)
    def start_route(self, route_id, **kwargs):
        route = self._route_for_employee(route_id)
        if not route:
            return self._error(_("Route not found."), 404)
        try:
            route.action_start()
        except Exception as error:
            return self._error(str(error))
        return self._success({"route": self._route_payload(route)})

    @http.route("/delivery/api/routes/<int:route_id>/complete", type="http", auth="user", methods=["POST"], csrf=False)
    def complete_route(self, route_id, **kwargs):
        route = self._route_for_employee(route_id)
        if not route:
            return self._error(_("Route not found."), 404)
        try:
            route.action_complete()
        except Exception as error:
            return self._error(str(error))
        return self._success({"route": self._route_payload(route)})

    @http.route("/delivery/api/stops/<int:line_id>/arrive", type="http", auth="user", methods=["POST"], csrf=False)
    def arrive(self, line_id, **kwargs):
        line = self._line_for_employee(line_id)
        if not line:
            return self._error(_("Stop not found."), 404)
        try:
            line.action_mark_arrived()
        except Exception as error:
            return self._error(str(error))
        return self._success({"stop": self._line_payload(line)})

    @http.route("/delivery/api/stops/<int:line_id>/deliver", type="http", auth="user", methods=["POST"], csrf=False)
    def deliver(self, line_id, **kwargs):
        line = self._line_for_employee(line_id)
        if not line:
            return self._error(_("Stop not found."), 404)
        try:
            line.action_mark_delivered()
        except Exception as error:
            return self._error(str(error))
        return self._success({"stop": self._line_payload(line)})

    @http.route("/delivery/api/stops/<int:line_id>/partial", type="http", auth="user", methods=["POST"], csrf=False)
    def partial(self, line_id, **kwargs):
        line = self._line_for_employee(line_id)
        if not line:
            return self._error(_("Stop not found."), 404)
        try:
            line.action_mark_partial()
        except Exception as error:
            return self._error(str(error))
        return self._success({"stop": self._line_payload(line)})

    @http.route("/delivery/api/stops/<int:line_id>/gps", type="http", auth="user", methods=["POST"], csrf=False)
    def gps(self, line_id, **kwargs):
        line = self._line_for_employee(line_id)
        if not line:
            return self._error(_("Stop not found."), 404)
        latitude = float(kwargs.get("latitude", 0.0) or 0.0)
        longitude = float(kwargs.get("longitude", 0.0) or 0.0)
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            return self._error(_("Invalid GPS coordinates."))
        line.write({"latitude": latitude, "longitude": longitude})
        request.env["delivery.event"].sudo().log_event("note", route=line.route_id, line=line, source="driver", latitude=latitude, longitude=longitude, description=_("GPS position updated."))
        return self._success({"latitude": latitude, "longitude": longitude})

    @http.route("/delivery/api/stops/<int:line_id>/note", type="http", auth="user", methods=["POST"], csrf=False)
    def note(self, line_id, **kwargs):
        line = self._line_for_employee(line_id)
        if not line:
            return self._error(_("Stop not found."), 404)
        note = kwargs.get("note", "")
        if not note:
            return self._error(_("A note is required."))
        line.message_post(body=note)
        request.env["delivery.event"].sudo().log_event("note", route=line.route_id, line=line, source="driver", description=note, is_customer_visible=False)
        return self._success()
