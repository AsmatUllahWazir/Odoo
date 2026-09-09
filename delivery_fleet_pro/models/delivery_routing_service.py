import json
import math
import urllib.error
import urllib.request
import urllib.parse
from odoo import api, models, _
from odoo.exceptions import UserError


class DeliveryRoutingService(models.AbstractModel):
    _name = "delivery.routing.service"
    _description = "Delivery Routing Provider Service"

    @api.model
    def get_config(self, company=None):
        return self.env["delivery.config"].sudo().get_company_config(company=company or self.env.company)

    @api.model
    def build_coordinates(self, lines, warehouse=None):
        points = []
        if warehouse:
            partner = warehouse.partner_id
            if partner.delivery_latitude and partner.delivery_longitude:
                points.append((partner.delivery_longitude, partner.delivery_latitude))
        for line in lines:
            if line.latitude and line.longitude:
                points.append((line.longitude, line.latitude))
        return points

    @api.model
    def route(self, lines, warehouse=None, provider=None, company=None):
        config = self.get_config(company)
        provider = provider or config.optimization_provider
        if provider == "heuristic":
            return self._heuristic(lines, warehouse)
        if provider == "openrouteservice":
            return self._openrouteservice(lines, warehouse, config)
        if provider == "google":
            return self._google(lines, warehouse, config)
        raise UserError(_("Unsupported routing provider: %s") % provider)

    @api.model
    def _heuristic(self, lines, warehouse):
        ordered = []
        remaining = list(lines)
        current = self._warehouse_point(warehouse)
        total_distance = 0.0
        total_duration = 0.0
        while remaining:
            candidate = min(remaining, key=lambda line: self._distance(current, self._line_point(line)))
            point = self._line_point(candidate)
            distance = self._distance(current, point)
            duration = distance / 35.0 if distance else 0.0
            ordered.append({"line": candidate, "distance": distance, "duration": duration})
            total_distance += distance
            total_duration += duration
            current = point
            remaining.remove(candidate)
        return {"provider": "heuristic", "ordered": ordered, "distance": total_distance, "duration": total_duration}

    @api.model
    def _openrouteservice(self, lines, warehouse, config):
        if not config.routing_api_key:
            raise UserError(_("OpenRouteService is selected but no API key is configured."))
        points = self.build_coordinates(lines, warehouse)
        if len(points) < 2:
            return self._heuristic(lines, warehouse)
        base_url = config.routing_base_url or "https://api.openrouteservice.org/v2/directions/driving-car/json"
        payload = json.dumps({"coordinates": points, "instructions": False}).encode()
        data = self._request_json(base_url, payload, {"Authorization": config.routing_api_key, "Content-Type": "application/json"})
        return self._parse_ors(data, lines)

    @api.model
    def _google(self, lines, warehouse, config):
        if not config.routing_api_key:
            raise UserError(_("Google routing is selected but no API key is configured."))
        points = self.build_coordinates(lines, warehouse)
        if len(points) < 2:
            return self._heuristic(lines, warehouse)
        base_url = config.routing_base_url or "https://maps.googleapis.com/maps/api/directions/json"
        origin = "%s,%s" % (points[0][1], points[0][0])
        destination = "%s,%s" % (points[-1][1], points[-1][0])
        waypoints = "|".join("%s,%s" % (point[1], point[0]) for point in points[1:-1])
        query = urllib.parse.urlencode({"origin": origin, "destination": destination, "waypoints": waypoints, "key": config.routing_api_key})
        data = self._request_json("%s?%s" % (base_url, query), None, {})
        return self._parse_google(data, lines)

    @api.model
    def _request_json(self, url, payload, headers):
        try:
            request = urllib.request.Request(url, data=payload, headers=headers, method="POST" if payload else "GET")
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as error:
            raise UserError(_("Routing provider request failed: %s") % error)

    @api.model
    def _parse_ors(self, data, lines):
        routes = data.get("routes") or []
        if not routes:
            raise UserError(_("OpenRouteService returned no route."))
        summary = routes[0].get("summary", {})
        return {"provider": "openrouteservice", "ordered": [{"line": line, "distance": 0.0, "duration": 0.0} for line in lines], "distance": summary.get("distance", 0.0) / 1000.0, "duration": summary.get("duration", 0.0) / 3600.0}

    @api.model
    def _parse_google(self, data, lines):
        if data.get("status") != "OK":
            raise UserError(_("Google routing returned status %s.") % data.get("status"))
        legs = (data.get("routes") or [{}])[0].get("legs") or []
        distance = sum((leg.get("distance") or {}).get("value", 0) for leg in legs) / 1000.0
        duration = sum((leg.get("duration") or {}).get("value", 0) for leg in legs) / 3600.0
        return {"provider": "google", "ordered": [{"line": line, "distance": 0.0, "duration": 0.0} for line in lines], "distance": distance, "duration": duration}

    @api.model
    def _warehouse_point(self, warehouse):
        if not warehouse:
            return (0.0, 0.0)
        partner = warehouse.partner_id
        return (partner.delivery_latitude or 0.0, partner.delivery_longitude or 0.0)

    @api.model
    def _line_point(self, line):
        return (line.latitude or 0.0, line.longitude or 0.0)

    @api.model
    def _distance(self, a, b):
        lat1, lon1 = a
        lat2, lon2 = b
        if not any([lat1, lon1, lat2, lon2]):
            return 0.0
        radius = 6371.0
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        value = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))
