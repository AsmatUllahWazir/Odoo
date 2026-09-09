import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryOptimizeRouteWizard(models.TransientModel):
    _name = "delivery.optimize.route.wizard"
    _description = "Optimize Delivery Route"

    route_id = fields.Many2one("delivery.route", required=True)
    strategy = fields.Selection(
        [("balanced", "Balanced"), ("distance", "Distance First"), ("time_window", "Time Windows First"), ("manual", "Manual")],
        default="balanced",
        required=True,
    )
    provider = fields.Selection(
        [("heuristic", "Built-in Heuristic"), ("openrouteservice", "OpenRouteService"), ("google", "Google Maps")],
        default="heuristic",
        required=True,
    )
    preserve_locked = fields.Boolean(default=True)
    recalculate_distance = fields.Boolean(default=True)
    start_latitude = fields.Float()
    start_longitude = fields.Float()
    average_speed_kmh = fields.Float(default=35.0)
    notes = fields.Text()

    def action_optimize(self):
        self.ensure_one()
        route = self.route_id
        if route.state not in ("draft", "planned"):
            raise UserError(_("Only draft or planned routes can be optimized."))
        lines = route.line_ids.sorted("sequence")
        if not lines:
            raise UserError(_("There are no stops to optimize."))
        if self.strategy == "manual":
            return True
        if self.provider == "heuristic":
            result = self.env["delivery.routing.service"].route(lines, route.warehouse_id, "heuristic", route.company_id)
        else:
            result = self.env["delivery.routing.service"].route(lines, route.warehouse_id, self.provider, route.company_id)
        ordered_data = result.get("ordered", [])
        ordered = [item["line"] for item in ordered_data] or self._nearest_neighbor(lines)
        for sequence, line in enumerate(ordered, 1):
            line.sequence = sequence * 10
        if self.recalculate_distance:
            if result.get("distance") is not None:
                route.estimated_distance = result.get("distance", 0.0)
                route.estimated_duration = result.get("duration", 0.0)
            self._recalculate_metrics(route, ordered)
        route.message_post(body=_("Route optimized using %s strategy and %s provider.") % (self.strategy, self.provider))
        return True

    def _nearest_neighbor(self, lines):
        remaining = list(lines)
        result = []
        current_lat = self.start_latitude or self.route_id.warehouse_id.partner_id.delivery_latitude
        current_lon = self.start_longitude or self.route_id.warehouse_id.partner_id.delivery_longitude
        while remaining:
            best = min(remaining, key=lambda line: self._score(line, current_lat, current_lon))
            result.append(best)
            remaining.remove(best)
            current_lat = best.latitude or current_lat
            current_lon = best.longitude or current_lon
        return result

    def _score(self, line, lat, lon):
        distance = self._distance_km(lat, lon, line.latitude, line.longitude)
        window_penalty = 0.0
        if self.strategy in ("balanced", "time_window") and line.date_from:
            window_penalty = max(0.0, (line.date_from.hour - 8) * 0.5)
        if self.strategy == "distance":
            return distance
        if self.strategy == "time_window":
            return distance + window_penalty * 10
        return distance + window_penalty

    def _distance_km(self, lat1, lon1, lat2, lon2):
        if not all([lat1, lon1, lat2, lon2]):
            return 0.0
        radius = 6371.0
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _recalculate_metrics(self, route, ordered):
        previous_lat = self.start_latitude or route.warehouse_id.partner_id.delivery_latitude
        previous_lon = self.start_longitude or route.warehouse_id.partner_id.delivery_longitude
        total_distance = 0.0
        total_duration = 0.0
        for line in ordered:
            distance = self._distance_km(previous_lat, previous_lon, line.latitude, line.longitude)
            duration = distance / self.average_speed_kmh if self.average_speed_kmh else 0.0
            line.write({"distance_from_previous": distance, "duration_from_previous": duration})
            total_distance += distance
            total_duration += duration + line.service_minutes / 60.0
            previous_lat = line.latitude or previous_lat
            previous_lon = line.longitude or previous_lon
        route.write({"estimated_distance": total_distance, "estimated_duration": total_duration})
