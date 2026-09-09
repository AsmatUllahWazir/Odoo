from odoo import api, fields, models


class DeliveryKPISnapshot(models.Model):
    _name = "delivery.kpi.snapshot"
    _description = "Delivery KPI Snapshot"
    _order = "snapshot_date desc, id desc"

    snapshot_date = fields.Date(required=True, default=fields.Date.context_today, index=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    warehouse_id = fields.Many2one("stock.warehouse", index=True)
    route_count = fields.Integer()
    stop_count = fields.Integer()
    delivered_count = fields.Integer()
    failed_count = fields.Integer()
    partial_count = fields.Integer()
    on_time_count = fields.Integer()
    total_distance = fields.Float()
    total_weight = fields.Float()
    revenue = fields.Monetary()
    cost = fields.Monetary()
    profit = fields.Monetary()
    on_time_percent = fields.Float()
    failed_percent = fields.Float()
    utilization_percent = fields.Float()
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True)

    _sql_constraints = [("snapshot_unique", "unique(snapshot_date, company_id, warehouse_id)", "A KPI snapshot already exists for this date and warehouse.")]

    @api.model
    def cron_create_daily_snapshots(self):
        for company in self.env["res.company"].search([]):
            warehouses = self.env["stock.warehouse"].search([("company_id", "=", company.id)])
            for warehouse in warehouses:
                self.create_snapshot(company=company, warehouse=warehouse)
        return True

    @api.model
    def create_snapshot(self, date=None, company=None, warehouse=None):
        date = date or fields.Date.today()
        company = company or self.env.company
        domain = [("date", "=", date), ("company_id", "=", company.id)]
        if warehouse:
            domain.append(("warehouse_id", "=", warehouse.id))
        routes = self.env["delivery.route"].search(domain)
        stops = routes.mapped("line_ids")
        delivered = stops.filtered(lambda line: line.status == "delivered")
        failed = stops.filtered(lambda line: line.status == "failed")
        on_time = stops.filtered("on_time")
        weight_capacity = sum(routes.mapped("vehicle_id.delivery_capacity_weight"))
        total_weight = sum(routes.mapped("total_weight"))
        snapshot = self.search([("snapshot_date", "=", date), ("company_id", "=", company.id), ("warehouse_id", "=", warehouse.id if warehouse else False)], limit=1)
        vals = {
            "snapshot_date": date,
            "company_id": company.id,
            "warehouse_id": warehouse.id if warehouse else False,
            "route_count": len(routes),
            "stop_count": len(stops),
            "delivered_count": len(delivered),
            "failed_count": len(failed),
            "partial_count": len(stops.filtered(lambda line: line.status == "partial")),
            "on_time_count": len(on_time),
            "total_distance": sum(routes.mapped("actual_distance")) or sum(routes.mapped("estimated_distance")),
            "total_weight": total_weight,
            "revenue": sum(routes.mapped("total_revenue")),
            "cost": sum(routes.mapped("total_cost")),
            "profit": sum(routes.mapped("profitability")),
            "on_time_percent": len(on_time) / len(stops) * 100 if stops else 0,
            "failed_percent": len(failed) / len(stops) * 100 if stops else 0,
            "utilization_percent": total_weight / weight_capacity * 100 if weight_capacity else 0,
        }
        return snapshot.write(vals) and snapshot or self.create(vals)
