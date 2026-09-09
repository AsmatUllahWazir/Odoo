from odoo import api, fields, models, tools


class DeliveryMetric(models.Model):
    _name = "delivery.metric"
    _description = "Delivery KPI"
    _auto = False
    _rec_name = "route_date"
    _depends = {
        "delivery.route": [
            "date", "company_id", "warehouse_id", "vehicle_id",
            "estimated_distance", "actual_distance", "total_weight",
            "total_revenue", "total_cost", "profitability",
        ],
        "delivery.route.line": ["route_id", "status", "on_time"],
        "fleet.vehicle": ["delivery_capacity_weight"],
    }

    route_date = fields.Date()
    company_id = fields.Many2one("res.company")
    warehouse_id = fields.Many2one("stock.warehouse")
    route_id = fields.Many2one("delivery.route")
    stop_count = fields.Integer()
    delivered_count = fields.Integer()
    failed_count = fields.Integer()
    partial_count = fields.Integer()
    on_time_count = fields.Integer()
    total_distance = fields.Float()
    total_weight = fields.Float()
    vehicle_capacity_weight = fields.Float()
    utilization_weight = fields.Float()
    revenue = fields.Float()
    cost = fields.Float()
    profit = fields.Float()
    on_time_percent = fields.Float()
    failed_percent = fields.Float()
    km_per_delivery = fields.Float()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW delivery_metric AS (
                SELECT
                    r.id AS id,
                    r.date AS route_date,
                    r.company_id AS company_id,
                    r.warehouse_id AS warehouse_id,
                    r.id AS route_id,
                    COUNT(l.id) AS stop_count,
                    COUNT(l.id) FILTER (WHERE l.status = 'delivered') AS delivered_count,
                    COUNT(l.id) FILTER (WHERE l.status = 'failed') AS failed_count,
                    COUNT(l.id) FILTER (WHERE l.status = 'partial') AS partial_count,
                    COUNT(l.id) FILTER (WHERE l.on_time) AS on_time_count,
                    COALESCE(NULLIF(r.actual_distance, 0), r.estimated_distance, 0) AS total_distance,
                    COALESCE(r.total_weight, 0) AS total_weight,
                    COALESCE(v.delivery_capacity_weight, 0) AS vehicle_capacity_weight,
                    CASE WHEN COALESCE(v.delivery_capacity_weight, 0) > 0
                        THEN COALESCE(r.total_weight, 0) / v.delivery_capacity_weight * 100 ELSE 0 END AS utilization_weight,
                    COALESCE(r.total_revenue, 0) AS revenue,
                    COALESCE(r.total_cost, 0) AS cost,
                    COALESCE(r.profitability, 0) AS profit,
                    CASE WHEN COUNT(l.id) > 0
                        THEN COUNT(l.id) FILTER (WHERE l.on_time)::numeric / COUNT(l.id) * 100 ELSE 0 END AS on_time_percent,
                    CASE WHEN COUNT(l.id) > 0
                        THEN COUNT(l.id) FILTER (WHERE l.status = 'failed')::numeric / COUNT(l.id) * 100 ELSE 0 END AS failed_percent,
                    CASE WHEN COUNT(l.id) FILTER (WHERE l.status = 'delivered') > 0
                        THEN COALESCE(NULLIF(r.actual_distance, 0), r.estimated_distance, 0) /
                             COUNT(l.id) FILTER (WHERE l.status = 'delivered') ELSE 0 END AS km_per_delivery
                FROM delivery_route r
                LEFT JOIN delivery_route_line l ON l.route_id = r.id
                LEFT JOIN fleet_vehicle v ON v.id = r.vehicle_id
                GROUP BY r.id, r.date, r.company_id, r.warehouse_id,
                         r.actual_distance, r.estimated_distance, r.total_weight,
                         r.total_revenue, r.total_cost, r.profitability,
                         v.delivery_capacity_weight
            )
            """
        )
