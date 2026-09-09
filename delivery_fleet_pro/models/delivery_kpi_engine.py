from datetime import timedelta
from odoo import api, fields, models, _


class DeliveryKPIEngine(models.AbstractModel):
    _name = "delivery.kpi.engine"
    _description = "Delivery KPI Calculation Engine"

    @api.model
    def route_kpis(self, route):
        lines = route.line_ids
        completed = lines.filtered(lambda line: line.status in ("delivered", "partial", "failed", "cancelled"))
        delivered = lines.filtered(lambda line: line.status == "delivered")
        failed = lines.filtered(lambda line: line.status == "failed")
        return {
            "route_id": route.id,
            "stops": len(lines),
            "completed": len(completed),
            "delivered": len(delivered),
            "failed": len(failed),
            "partial": len(lines.filtered(lambda line: line.status == "partial")),
            "on_time": len(lines.filtered("on_time")),
            "on_time_percent": self._percent(len(lines.filtered("on_time")), len(lines)),
            "failed_percent": self._percent(len(failed), len(lines)),
            "completion_percent": self._percent(len(completed), len(lines)),
            "km_per_delivery": route.estimated_distance / len(delivered) if delivered and route.estimated_distance else 0.0,
            "weight_utilization": route.capacity_weight_utilization,
            "volume_utilization": route.capacity_volume_utilization,
            "revenue": route.total_revenue,
            "cost": route.total_cost,
            "profit": route.profitability,
            "margin_percent": route.margin_percent,
        }

    @api.model
    def driver_kpis(self, driver, date_from=False, date_to=False):
        domain = [("driver_id", "=", driver.id)]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        routes = self.env["delivery.route"].search(domain)
        lines = routes.mapped("line_ids")
        delivered = lines.filtered(lambda line: line.status == "delivered")
        failed = lines.filtered(lambda line: line.status == "failed")
        return {
            "driver_id": driver.id,
            "route_count": len(routes),
            "stop_count": len(lines),
            "delivered_count": len(delivered),
            "failed_count": len(failed),
            "partial_count": len(lines.filtered(lambda line: line.status == "partial")),
            "on_time_percent": self._percent(len(lines.filtered("on_time")), len(lines)),
            "failed_percent": self._percent(len(failed), len(lines)),
            "distance_km": sum(routes.mapped("actual_distance")) or sum(routes.mapped("estimated_distance")),
            "hours": sum(routes.mapped("actual_duration")) or sum(routes.mapped("estimated_duration")),
            "revenue": sum(routes.mapped("total_revenue")),
            "cost": sum(routes.mapped("total_cost")),
            "profit": sum(routes.mapped("profitability")),
        }

    @api.model
    def vehicle_kpis(self, vehicle, date_from=False, date_to=False):
        domain = [("vehicle_id", "=", vehicle.id)]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        routes = self.env["delivery.route"].search(domain)
        lines = routes.mapped("line_ids")
        return {
            "vehicle_id": vehicle.id,
            "route_count": len(routes),
            "stop_count": len(lines),
            "distance_km": sum(routes.mapped("actual_distance")) or sum(routes.mapped("estimated_distance")),
            "weight": sum(routes.mapped("total_weight")),
            "volume": sum(routes.mapped("total_volume")),
            "revenue": sum(routes.mapped("total_revenue")),
            "cost": sum(routes.mapped("total_cost")),
            "profit": sum(routes.mapped("profitability")),
        }

    @api.model
    def warehouse_kpis(self, warehouse, date_from=False, date_to=False):
        domain = [("warehouse_id", "=", warehouse.id)]
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        routes = self.env["delivery.route"].search(domain)
        lines = routes.mapped("line_ids")
        delivered = lines.filtered(lambda line: line.status == "delivered")
        return {
            "warehouse_id": warehouse.id,
            "route_count": len(routes),
            "stop_count": len(lines),
            "delivered_count": len(delivered),
            "failed_count": len(lines.filtered(lambda line: line.status == "failed")),
            "on_time_percent": self._percent(len(lines.filtered("on_time")), len(lines)),
            "distance_km": sum(routes.mapped("actual_distance")) or sum(routes.mapped("estimated_distance")),
            "profit": sum(routes.mapped("profitability")),
        }

    @api.model
    def period_kpis(self, date_from, date_to, company=None):
        company = company or self.env.company
        routes = self.env["delivery.route"].search([
            ("company_id", "=", company.id),
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ])
        lines = routes.mapped("line_ids")
        delivered = lines.filtered(lambda line: line.status == "delivered")
        failed = lines.filtered(lambda line: line.status == "failed")
        return {
            "date_from": date_from,
            "date_to": date_to,
            "route_count": len(routes),
            "stop_count": len(lines),
            "delivered_count": len(delivered),
            "failed_count": len(failed),
            "partial_count": len(lines.filtered(lambda line: line.status == "partial")),
            "on_time_percent": self._percent(len(lines.filtered("on_time")), len(lines)),
            "failed_percent": self._percent(len(failed), len(lines)),
            "distance_km": sum(routes.mapped("actual_distance")) or sum(routes.mapped("estimated_distance")),
            "revenue": sum(routes.mapped("total_revenue")),
            "cost": sum(routes.mapped("total_cost")),
            "profit": sum(routes.mapped("profitability")),
        }

    @api.model
    def trend(self, company=None, days=30):
        company = company or self.env.company
        today = fields.Date.today()
        result = []
        for offset in range(days - 1, -1, -1):
            date = today - timedelta(days=offset)
            result.append(self.period_kpis(date, date, company=company))
        return result

    @api.model
    def _percent(self, numerator, denominator):
        return numerator / denominator * 100 if denominator else 0.0

    @api.model
    def command_center(self, date_from, date_to, company=None):
        company = company or self.env.company
        routes = self.env["delivery.route"].search([("company_id", "=", company.id), ("date", ">=", date_from), ("date", "<=", date_to)])
        lines = routes.mapped("line_ids")
        exceptions = self.env["delivery.exception"].search([("company_id", "=", company.id), ("detected_at", ">=", fields.Datetime.to_datetime(str(date_from) + " 00:00:00")), ("detected_at", "<=", fields.Datetime.to_datetime(str(date_to) + " 23:59:59"))])
        vehicles = self.env["fleet.vehicle"].search([("company_id", "=", company.id)])
        drivers = self.env["hr.employee"].search([("company_id", "=", company.id), ("delivery_available", "=", True)])
        delivered = lines.filtered(lambda l: l.status == "delivered")
        completed = lines.filtered(lambda l: l.status in ("delivered", "partial", "failed", "cancelled"))
        return {
            "kpis": self.period_kpis(date_from, date_to, company=company),
            "completion_percent": self._percent(len(completed), len(lines)),
            "average_stop_minutes": sum(lines.mapped("delivery_duration_minutes")) / len(completed) if completed else 0.0,
            "revenue_per_km": sum(routes.mapped("total_revenue")) / (sum(routes.mapped("actual_distance")) or sum(routes.mapped("estimated_distance")) or 1.0),
            "cost_per_delivery": sum(routes.mapped("total_cost")) / len(delivered) if delivered else 0.0,
            "open_exceptions": len(exceptions.filtered(lambda e: e.state in ("open", "acknowledged", "in_progress"))),
            "critical_exceptions": len(exceptions.filtered(lambda e: e.priority == "3" and e.state not in ("resolved", "cancelled"))),
            "active_routes": len(routes.filtered(lambda r: r.state in ("dispatched", "in_transit"))),
            "ready_routes": len(routes.filtered(lambda r: r.readiness_state == "ready")),
            "at_risk_routes": len(routes.filtered(lambda r: r.readiness_state != "ready" and r.state in ("draft", "planned", "dispatched"))),
            "fleet": {
                "total": len(vehicles),
                "available": len(vehicles.filtered(lambda v: v.delivery_status == "available")),
                "maintenance": len(vehicles.filtered(lambda v: v.delivery_status == "maintenance")),
                "assigned": len(vehicles.filtered(lambda v: v.delivery_status == "assigned")),
            },
            "drivers": {
                "available": len(drivers),
                "busy": len(routes.filtered(lambda r: r.state in ("planned", "dispatched", "in_transit")).mapped("driver_id")),
            },
            "states": [{"state": state, "label": dict(self.env["delivery.route"]._fields["state"].selection).get(state, state), "count": len(routes.filtered(lambda r, s=state: r.state == s))} for state in ["draft", "planned", "dispatched", "in_transit", "done", "partial", "failed", "cancelled"]],
            "exceptions": [{"id": e.id, "name": e.name, "type": e.exception_type, "priority": e.priority, "state": e.state, "route": e.route_id.name, "stop": e.route_line_id.display_name if e.route_line_id else "", "age": round(e.age_minutes, 0)} for e in exceptions.filtered(lambda e: e.state not in ("resolved", "cancelled"))[:12]],
            "vehicles": [{"id": v.id, "name": v.display_name, "status": v.delivery_status, "capacity_weight": v.delivery_capacity_weight, "capacity_volume": v.delivery_capacity_volume, "route_count": len(routes.filtered(lambda r, vid=v.id: r.vehicle_id.id == vid))} for v in vehicles[:12]],
        }

    @api.model
    def trend_compare(self, date_from, date_to, company=None):
        company = company or self.env.company
        start = fields.Date.to_date(date_from)
        end = fields.Date.to_date(date_to)
        days = max(1, (end - start).days + 1)
        previous_end = start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=days - 1)
        current = self.period_kpis(start, end, company=company)
        previous = self.period_kpis(previous_start, previous_end, company=company)
        result = {}
        for key in ("route_count", "stop_count", "delivered_count", "failed_count", "distance_km", "revenue", "cost", "profit"):
            old = previous.get(key) or 0.0
            new = current.get(key) or 0.0
            result[key] = {"value": new, "previous": old, "change_percent": ((new - old) / abs(old) * 100) if old else (100.0 if new else 0.0)}
        return result

# Advanced dashboard helpers are intentionally kept in the existing KPI engine so
# the command center remains a single, lightweight client action.
