from datetime import timedelta
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class DeliveryException(models.Model):
    _name = "delivery.exception"
    _description = "Delivery Operational Exception"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, create_date desc, id desc"

    name = fields.Char(required=True, copy=False, default="New", tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    route_id = fields.Many2one("delivery.route", required=True, ondelete="cascade", index=True, tracking=True)
    route_line_id = fields.Many2one("delivery.route.line", ondelete="cascade", tracking=True)
    picking_id = fields.Many2one("stock.picking", related="route_line_id.picking_id", store=True)
    partner_id = fields.Many2one("res.partner", related="route_line_id.partner_id", store=True)
    driver_id = fields.Many2one("hr.employee", related="route_id.driver_id", store=True)
    vehicle_id = fields.Many2one("fleet.vehicle", related="route_id.vehicle_id", store=True)
    exception_type = fields.Selection([
        ("late", "Late Delivery"), ("capacity", "Capacity"), ("vehicle", "Vehicle"),
        ("driver", "Driver"), ("address", "Address / GPS"), ("customer", "Customer"),
        ("pod", "POD / Verification"), ("system", "System"), ("other", "Other")
    ], required=True, default="other", tracking=True)
    priority = fields.Selection([("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Critical")], default="1", tracking=True)
    state = fields.Selection([
        ("open", "Open"), ("acknowledged", "Acknowledged"), ("in_progress", "In Progress"),
        ("resolved", "Resolved"), ("cancelled", "Cancelled")
    ], default="open", required=True, tracking=True, index=True)
    detected_at = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    acknowledged_at = fields.Datetime(readonly=True)
    resolved_at = fields.Datetime(readonly=True)
    sla_minutes = fields.Integer(default=60)
    age_minutes = fields.Float(compute="_compute_age")
    description = fields.Text(required=True)
    resolution = fields.Text()
    owner_id = fields.Many2one("res.users", tracking=True)
    customer_visible = fields.Boolean(default=False)
    auto_created = fields.Boolean(default=False)

    @api.depends("detected_at", "state", "resolved_at")
    def _compute_age(self):
        now = fields.Datetime.now()
        for rec in self:
            end = rec.resolved_at if rec.state == "resolved" and rec.resolved_at else now
            rec.age_minutes = max(0.0, (end - rec.detected_at).total_seconds() / 60.0) if rec.detected_at else 0.0

    @api.constrains("route_id", "route_line_id", "company_id")
    def _check_context(self):
        for rec in self:
            if rec.route_id and rec.route_id.company_id != rec.company_id:
                raise ValidationError(_("Exception company must match route company."))
            if rec.route_line_id and rec.route_line_id.route_id != rec.route_id:
                raise ValidationError(_("Exception stop must belong to the selected route."))

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = seq.next_by_code("delivery.exception") or "EXC/%s" % fields.Date.today()
            vals.setdefault("company_id", self.env.company.id)
        return super().create(vals_list)

    def action_acknowledge(self):
        self.write({"state": "acknowledged", "acknowledged_at": fields.Datetime.now(), "owner_id": self.env.user.id})
        return True

    def action_start(self):
        self.write({"state": "in_progress", "owner_id": self.env.user.id})
        return True

    def action_resolve(self):
        for rec in self:
            if not rec.resolution:
                raise UserError(_("Please enter a resolution before closing an exception."))
        self.write({"state": "resolved", "resolved_at": fields.Datetime.now()})
        return True

    def action_cancel(self):
        self.write({"state": "cancelled", "resolved_at": fields.Datetime.now()})
        return True


class DeliveryRouteAdvanced(models.Model):
    _inherit = "delivery.route"

    priority = fields.Selection([("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Critical")], default="1", tracking=True, index=True)
    dispatch_notes = fields.Text()
    loading_start = fields.Datetime()
    loading_end = fields.Datetime()
    handover_confirmed = fields.Boolean(default=False, tracking=True)
    driver_acknowledged = fields.Boolean(default=False, tracking=True)
    driver_acknowledged_at = fields.Datetime(readonly=True)
    departure_odometer = fields.Float()
    arrival_odometer = fields.Float()
    odometer_distance = fields.Float(compute="_compute_advanced_metrics", store=True)
    planned_stop_minutes = fields.Float(compute="_compute_advanced_metrics", store=True)
    actual_stop_minutes = fields.Float(compute="_compute_advanced_metrics", store=True)
    average_stop_minutes = fields.Float(compute="_compute_advanced_metrics", store=True)
    completion_percent = fields.Float(compute="_compute_advanced_metrics", store=True)
    route_efficiency_percent = fields.Float(compute="_compute_advanced_metrics", store=True)
    revenue_per_km = fields.Monetary(compute="_compute_advanced_metrics", store=True)
    cost_per_km = fields.Monetary(compute="_compute_advanced_metrics", store=True)
    profit_per_stop = fields.Monetary(compute="_compute_advanced_metrics", store=True)
    exception_ids = fields.One2many("delivery.exception", "route_id")
    exception_count = fields.Integer(compute="_compute_exception_count", store=True)
    open_exception_count = fields.Integer(compute="_compute_exception_count", store=True)
    sla_breached = fields.Boolean(compute="_compute_sla_health", store=True)
    sla_breach_count = fields.Integer(compute="_compute_sla_health", store=True)
    service_level_percent = fields.Float(compute="_compute_sla_health", store=True)
    readiness_score = fields.Float(compute="_compute_readiness", store=True)
    readiness_state = fields.Selection([("ready", "Ready"), ("warning", "Needs Attention"), ("blocked", "Blocked")], compute="_compute_readiness", store=True)

    @api.depends("line_ids.status", "line_ids.service_minutes", "line_ids.delivery_duration_minutes", "estimated_distance", "actual_distance", "total_revenue", "total_cost", "arrival_odometer", "departure_odometer")
    def _compute_advanced_metrics(self):
        for route in self:
            lines = route.line_ids
            completed = lines.filtered(lambda l: l.status in ("delivered", "partial", "failed", "cancelled"))
            planned = sum(lines.mapped("service_minutes"))
            actual = sum(lines.mapped("delivery_duration_minutes"))
            distance = route.actual_distance or route.estimated_distance
            route.odometer_distance = max(0.0, route.arrival_odometer - route.departure_odometer) if route.arrival_odometer and route.departure_odometer else 0.0
            route.planned_stop_minutes = planned
            route.actual_stop_minutes = actual
            route.average_stop_minutes = actual / len(completed) if completed else 0.0
            route.completion_percent = len(completed) / len(lines) * 100 if lines else 0.0
            route.route_efficiency_percent = (route.estimated_distance / distance * 100) if distance and route.estimated_distance else 0.0
            route.revenue_per_km = route.total_revenue / distance if distance else 0.0
            route.cost_per_km = route.total_cost / distance if distance else 0.0
            route.profit_per_stop = route.profitability / len(lines) if lines else 0.0

    @api.depends("exception_ids.state")
    def _compute_exception_count(self):
        for route in self:
            route.exception_count = len(route.exception_ids)
            route.open_exception_count = len(route.exception_ids.filtered(lambda e: e.state in ("open", "acknowledged", "in_progress")))

    @api.depends("line_ids.on_time", "line_ids.status", "sla_id", "line_ids.late_minutes")
    def _compute_sla_health(self):
        for route in self:
            lines = route.line_ids
            breaches = lines.filtered(lambda l: l.status in ("delivered", "partial") and l.late_minutes > (route.sla_id.tolerance_minutes if route.sla_id else 0))
            eligible = lines.filtered(lambda l: l.status in ("delivered", "partial", "failed"))
            route.sla_breach_count = len(breaches)
            route.sla_breached = bool(breaches)
            route.service_level_percent = (len(eligible - breaches) / len(eligible) * 100) if eligible else 0.0

    @api.depends("driver_id", "vehicle_id", "line_ids.partner_id", "line_ids.latitude", "line_ids.longitude", "total_weight", "total_volume", "state", "service_type_id")
    def _compute_readiness(self):
        for route in self:
            score = 100.0
            blocked = False
            if not route.driver_id:
                score -= 25; blocked = True
            if not route.vehicle_id:
                score -= 25; blocked = True
            if route.vehicle_id and route.vehicle_id.delivery_capacity_weight and route.total_weight > route.vehicle_id.delivery_capacity_weight:
                score -= 30; blocked = True
            if route.vehicle_id and route.vehicle_id.delivery_capacity_volume and route.total_volume > route.vehicle_id.delivery_capacity_volume:
                score -= 20; blocked = True
            missing_gps = len(route.line_ids.filtered(lambda l: not l.latitude or not l.longitude))
            if missing_gps:
                score -= min(15, missing_gps * 2)
            if not route.line_ids:
                score -= 20
            route.readiness_score = max(0.0, score)
            route.readiness_state = "blocked" if blocked else ("ready" if score >= 90 else "warning")

    def action_acknowledge_by_driver(self):
        for route in self:
            if route.state not in ("dispatched", "in_transit"):
                raise UserError(_("Only dispatched or in-transit routes can be acknowledged."))
            route.write({"driver_acknowledged": True, "driver_acknowledged_at": fields.Datetime.now(), "handover_confirmed": True})
            self.env["delivery.event"].log_event("note", route=route, description=_("Driver acknowledged route handover."), source="driver")
        return True

    def action_recalculate_operational_metrics(self):
        self._compute_advanced_metrics()
        self._compute_exception_count()
        self._compute_sla_health()
        self._compute_readiness()
        return True

    def action_create_exception(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("New Delivery Exception"),
            "res_model": "delivery.exception",
            "view_mode": "form",
            "target": "new",
            "context": {"default_route_id": self.id, "default_company_id": self.company_id.id},
        }

    def _auto_create_operational_exceptions(self):
        Exception = self.env["delivery.exception"]
        for route in self:
            if route.capacity_weight_utilization > 100 and not Exception.search_count([("route_id", "=", route.id), ("exception_type", "=", "capacity"), ("state", "!=", "cancelled")]):
                Exception.create({"route_id": route.id, "exception_type": "capacity", "priority": "3", "description": _("Weight capacity is above 100% before dispatch."), "auto_created": True})
            if route.capacity_volume_utilization > 100 and not Exception.search_count([("route_id", "=", route.id), ("exception_type", "=", "capacity"), ("state", "!=", "cancelled")]):
                Exception.create({"route_id": route.id, "exception_type": "capacity", "priority": "3", "description": _("Volume capacity is above 100% before dispatch."), "auto_created": True})
            missing = route.line_ids.filtered(lambda l: not l.latitude or not l.longitude)
            if missing and route.state in ("planned", "dispatched"):
                Exception.create({"route_id": route.id, "exception_type": "address", "priority": "2", "description": _("%s stop(s) do not have usable GPS coordinates.") % len(missing), "auto_created": True})

    @api.model
    def cron_scan_operational_exceptions(self):
        routes = self.search([("state", "in", ["draft", "planned", "dispatched", "in_transit"])], limit=500)
        routes._auto_create_operational_exceptions()
        late_lines = self.env["delivery.route.line"].search([("status", "in", ["assigned", "in_transit", "arrived"]), ("date_to", "!=", False), ("date_to", "<", fields.Datetime.now())], limit=500)
        Exception = self.env["delivery.exception"]
        for line in late_lines:
            if not Exception.search_count([("route_line_id", "=", line.id), ("exception_type", "=", "late"), ("state", "not in", ["resolved", "cancelled"]) ]):
                Exception.create({"route_id": line.route_id.id, "route_line_id": line.id, "exception_type": "late", "priority": "2", "description": _("Stop %s is past its promised delivery window.") % line.sequence, "auto_created": True})
        return True

    def action_dispatch(self):
        res = super().action_dispatch()
        self._auto_create_operational_exceptions()
        return res


class DeliveryRouteLineAdvanced(models.Model):
    _inherit = "delivery.route.line"

    priority = fields.Selection([("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Critical")], default="1", tracking=True, index=True)
    customer_reference = fields.Char(related="picking_id.origin", store=True, readonly=True)
    delivery_instructions = fields.Text(related="partner_id.delivery_instructions", readonly=True)
    access_code = fields.Char(string="Access Code")
    cod_amount = fields.Monetary(string="Cash on Delivery")
    cod_collected = fields.Boolean(string="COD Collected", tracking=True)
    cod_collected_at = fields.Datetime(readonly=True)
    customer_rating = fields.Selection([("1", "1 - Very Poor"), ("2", "2 - Poor"), ("3", "3 - Average"), ("4", "4 - Good"), ("5", "5 - Excellent")], tracking=True)
    customer_feedback = fields.Text()
    geofence_radius_m = fields.Integer(default=250)
    checkin_latitude = fields.Float(digits=(10, 7))
    checkin_longitude = fields.Float(digits=(10, 7))
    checkout_latitude = fields.Float(digits=(10, 7))
    checkout_longitude = fields.Float(digits=(10, 7))
    gps_distance_to_customer_m = fields.Float(compute="_compute_gps_distance", store=True)
    gps_checkin_valid = fields.Boolean(compute="_compute_gps_distance", store=True)
    waiting_minutes = fields.Float(default=0.0)
    reschedule_count = fields.Integer(default=0)
    promised_datetime = fields.Datetime(compute="_compute_promised_datetime", store=True)
    service_variance_minutes = fields.Float(compute="_compute_service_variance", store=True)
    delivery_cycle_minutes = fields.Float(compute="_compute_delivery_cycle", store=True)
    exception_ids = fields.One2many("delivery.exception", "route_line_id")
    exception_count = fields.Integer(compute="_compute_line_exception_count", store=True)

    @api.depends("checkin_latitude", "checkin_longitude", "latitude", "longitude", "geofence_radius_m")
    def _compute_gps_distance(self):
        import math
        for line in self:
            if not all([line.checkin_latitude, line.checkin_longitude, line.latitude, line.longitude]):
                line.gps_distance_to_customer_m = 0.0
                line.gps_checkin_valid = False
                continue
            r = 6371000.0
            p1, p2 = math.radians(line.checkin_latitude), math.radians(line.latitude)
            dp, dl = math.radians(line.latitude - line.checkin_latitude), math.radians(line.longitude - line.checkin_longitude)
            a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
            line.gps_distance_to_customer_m = r * 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1 - a)))
            line.gps_checkin_valid = line.gps_distance_to_customer_m <= (line.geofence_radius_m or 250)

    @api.depends("date_from", "date_to", "route_id.planned_start")
    def _compute_promised_datetime(self):
        for line in self:
            line.promised_datetime = line.date_to or line.date_from or line.route_id.planned_start

    @api.depends("arrival_time", "departure_time", "promised_datetime")
    def _compute_service_variance(self):
        for line in self:
            if line.arrival_time and line.promised_datetime:
                line.service_variance_minutes = (line.arrival_time - line.promised_datetime).total_seconds() / 60.0
            else:
                line.service_variance_minutes = 0.0

    @api.depends("arrival_time", "departure_time")
    def _compute_delivery_cycle(self):
        for line in self:
            if line.arrival_time and line.departure_time:
                line.delivery_cycle_minutes = max(0.0, (line.departure_time - line.arrival_time).total_seconds() / 60.0)
            else:
                line.delivery_cycle_minutes = 0.0

    @api.depends("exception_ids.state")
    def _compute_line_exception_count(self):
        for line in self:
            line.exception_count = len(line.exception_ids.filtered(lambda e: e.state != "cancelled"))

    def action_check_in_gps(self, latitude, longitude):
        for line in self:
            if line.status not in ("assigned", "in_transit", "arrived"):
                raise UserError(_("This stop is not ready for GPS check-in."))
            line.write({"checkin_latitude": latitude, "checkin_longitude": longitude, "arrival_time": line.arrival_time or fields.Datetime.now(), "status": "arrived"})
            if not line.gps_checkin_valid:
                self.env["delivery.exception"].create({"route_id": line.route_id.id, "route_line_id": line.id, "exception_type": "address", "priority": "2", "description": _("Driver checked in %.0f m away from the customer geofence.") % line.gps_distance_to_customer_m, "auto_created": True})
            return True
        return False

    def action_collect_cod(self):
        for line in self:
            if line.cod_amount <= 0:
                raise UserError(_("This stop has no COD amount."))
            line.write({"cod_collected": True, "cod_collected_at": fields.Datetime.now()})
            self.env["delivery.event"].log_event("note", route=line.route_id, line=line, description=_("COD collected: %s") % line.cod_amount, source="driver")
        return True

    def action_reschedule(self):
        for line in self:
            if line.status in ("delivered", "cancelled"):
                raise UserError(_("A delivered or cancelled stop cannot be rescheduled."))
            line.write({"reschedule_count": line.reschedule_count + 1, "status": "retry", "retry_date": fields.Date.today() + timedelta(days=1)})
            self.env["delivery.exception"].create({"route_id": line.route_id.id, "route_line_id": line.id, "exception_type": "customer", "priority": "1", "description": _("Delivery rescheduled by operations."), "auto_created": False})
        return True

    def write(self, vals):
        old_states = {line.id: line.status for line in self} if "status" in vals else {}
        res = super().write(vals)
        if "status" in vals:
            for line in self:
                if old_states.get(line.id) != line.status:
                    self.env["delivery.audit"].log("state", line, old_value=old_states.get(line.id), new_value=line.status, route=line.route_id, line=line)
        return res
