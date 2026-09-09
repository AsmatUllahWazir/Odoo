from odoo import fields, models, tools


class DeliveryDriverPerformance(models.Model):
    _name = "delivery.driver.performance"
    _description = "Driver Performance"
    _auto = False
    _rec_name = "driver_id"
    _depends = {
        "hr.employee": ["company_id"],
        "delivery.route": [
            "driver_id", "actual_distance", "estimated_distance",
            "actual_duration", "estimated_duration", "total_revenue",
            "total_cost", "profitability",
        ],
        "delivery.route.line": ["route_id", "status", "on_time"],
    }

    driver_id = fields.Many2one("hr.employee")
    company_id = fields.Many2one("res.company")
    route_count = fields.Integer()
    stop_count = fields.Integer()
    delivered_count = fields.Integer()
    failed_count = fields.Integer()
    partial_count = fields.Integer()
    on_time_count = fields.Integer()
    distance_km = fields.Float()
    delivery_hours = fields.Float()
    revenue = fields.Float()
    cost = fields.Float()
    profit = fields.Float()
    on_time_percent = fields.Float()
    failed_percent = fields.Float()
    stops_per_route = fields.Float()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW delivery_driver_performance AS (
                WITH route_agg AS (
                    SELECT driver_id, COUNT(*) AS route_count,
                           COALESCE(SUM(COALESCE(NULLIF(actual_distance, 0), estimated_distance, 0)), 0) AS distance_km,
                           COALESCE(SUM(COALESCE(NULLIF(actual_duration, 0), estimated_duration, 0)), 0) AS delivery_hours,
                           COALESCE(SUM(total_revenue), 0) AS revenue,
                           COALESCE(SUM(total_cost), 0) AS cost,
                           COALESCE(SUM(profitability), 0) AS profit
                    FROM delivery_route
                    WHERE driver_id IS NOT NULL
                    GROUP BY driver_id
                ),
                line_agg AS (
                    SELECT r.driver_id, COUNT(l.id) AS stop_count,
                           COUNT(l.id) FILTER (WHERE l.status = 'delivered') AS delivered_count,
                           COUNT(l.id) FILTER (WHERE l.status = 'failed') AS failed_count,
                           COUNT(l.id) FILTER (WHERE l.status = 'partial') AS partial_count,
                           COUNT(l.id) FILTER (WHERE l.on_time) AS on_time_count
                    FROM delivery_route r
                    JOIN delivery_route_line l ON l.route_id = r.id
                    WHERE r.driver_id IS NOT NULL
                    GROUP BY r.driver_id
                )
                SELECT
                    e.id AS id, e.id AS driver_id, e.company_id AS company_id,
                    COALESCE(ra.route_count, 0) AS route_count,
                    COALESCE(la.stop_count, 0) AS stop_count,
                    COALESCE(la.delivered_count, 0) AS delivered_count,
                    COALESCE(la.failed_count, 0) AS failed_count,
                    COALESCE(la.partial_count, 0) AS partial_count,
                    COALESCE(la.on_time_count, 0) AS on_time_count,
                    COALESCE(ra.distance_km, 0) AS distance_km,
                    COALESCE(ra.delivery_hours, 0) AS delivery_hours,
                    COALESCE(ra.revenue, 0) AS revenue,
                    COALESCE(ra.cost, 0) AS cost,
                    COALESCE(ra.profit, 0) AS profit,
                    CASE WHEN COALESCE(la.stop_count, 0) > 0 THEN COALESCE(la.on_time_count, 0)::numeric / la.stop_count * 100 ELSE 0 END AS on_time_percent,
                    CASE WHEN COALESCE(la.stop_count, 0) > 0 THEN COALESCE(la.failed_count, 0)::numeric / la.stop_count * 100 ELSE 0 END AS failed_percent,
                    CASE WHEN COALESCE(ra.route_count, 0) > 0 THEN COALESCE(la.stop_count, 0)::numeric / ra.route_count ELSE 0 END AS stops_per_route
                FROM hr_employee e
                LEFT JOIN route_agg ra ON ra.driver_id = e.id
                LEFT JOIN line_agg la ON la.driver_id = e.id
            )
            """
        )
