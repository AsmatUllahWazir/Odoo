import math
import secrets
from datetime import timedelta
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class DeliveryRoute(models.Model):
    _name = "delivery.route"
    _description = "Delivery Route"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(required=True, copy=False, default="New", tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    date = fields.Date(required=True, default=fields.Date.context_today, tracking=True, index=True)
    warehouse_id = fields.Many2one("stock.warehouse", required=True, tracking=True, index=True)
    template_id = fields.Many2one("delivery.route.template", tracking=True)
    zone_id = fields.Many2one("delivery.zone", tracking=True)
    vehicle_id = fields.Many2one("fleet.vehicle", tracking=True)
    driver_id = fields.Many2one("hr.employee", tracking=True)
    service_type_id = fields.Many2one("delivery.service.type", tracking=True)
    sla_id = fields.Many2one("delivery.sla", tracking=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("planned", "Planned"),
            ("dispatched", "Dispatched"),
            ("in_transit", "In Transit"),
            ("done", "Done"),
            ("partial", "Partial"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )
    line_ids = fields.One2many("delivery.route.line", "route_id", string="Stops", copy=True)
    event_ids = fields.One2many("delivery.event", "route_id", string="Events")
    segment_ids = fields.One2many("delivery.route.segment", "route_id", string="Segments")
    charge_ids = fields.One2many("delivery.route.charge", "route_id", string="Charges")
    cost_line_ids = fields.One2many("delivery.route.cost", "route_id", string="Cost Lines")
    tracking_link_ids = fields.One2many("delivery.tracking.link", "route_id")
    stop_count = fields.Integer(compute="_compute_counts", store=True)
    delivered_count = fields.Integer(compute="_compute_counts", store=True)
    failed_count = fields.Integer(compute="_compute_counts", store=True)
    partial_count = fields.Integer(compute="_compute_counts", store=True)
    pending_count = fields.Integer(compute="_compute_counts", store=True)
    on_time_count = fields.Integer(compute="_compute_counts", store=True)
    total_weight = fields.Float(compute="_compute_totals", store=True)
    total_volume = fields.Float(compute="_compute_totals", store=True)
    total_packages = fields.Float(compute="_compute_totals", store=True)
    total_revenue = fields.Monetary(compute="_compute_financials", store=True)
    total_cost = fields.Monetary(compute="_compute_financials", store=True)
    profitability = fields.Monetary(compute="_compute_financials", store=True)
    margin_percent = fields.Float(compute="_compute_financials", store=True)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True)
    estimated_distance = fields.Float(string="Estimated Distance (km)")
    actual_distance = fields.Float(string="Actual Distance (km)")
    estimated_duration = fields.Float(string="Estimated Duration (hours)")
    actual_duration = fields.Float(string="Actual Duration (hours)")
    planned_start = fields.Datetime()
    planned_end = fields.Datetime()
    actual_start = fields.Datetime()
    actual_end = fields.Datetime()
    fuel_liters = fields.Float()
    driver_hours = fields.Float()
    vehicle_hours = fields.Float()
    capacity_weight_utilization = fields.Float(compute="_compute_utilization", store=True)
    capacity_volume_utilization = fields.Float(compute="_compute_utilization", store=True)
    tracking_token = fields.Char(copy=False, index=True)
    public_url = fields.Char(compute="_compute_public_url")
    notes = fields.Text()

    @api.depends("line_ids.status", "line_ids.on_time")
    def _compute_counts(self):
        for route in self:
            statuses = route.line_ids.mapped("status")
            route.stop_count = len(statuses)
            route.delivered_count = statuses.count("delivered")
            route.failed_count = statuses.count("failed")
            route.partial_count = statuses.count("partial")
            route.pending_count = sum(1 for status in statuses if status in ("pending", "assigned", "in_transit", "retry"))
            route.on_time_count = sum(1 for line in route.line_ids if line.on_time)

    @api.depends("line_ids.weight", "line_ids.volume", "line_ids.package_count")
    def _compute_totals(self):
        for route in self:
            route.total_weight = sum(route.line_ids.mapped("weight"))
            route.total_volume = sum(route.line_ids.mapped("volume"))
            route.total_packages = sum(route.line_ids.mapped("package_count"))

    @api.depends("line_ids.revenue", "line_ids.cost_total", "cost_line_ids.amount")
    def _compute_financials(self):
        for route in self:
            route.total_revenue = sum(route.line_ids.mapped("revenue"))
            explicit_cost = sum(route.cost_line_ids.mapped("amount"))
            route.total_cost = explicit_cost if explicit_cost else sum(route.line_ids.mapped("cost_total"))
            route.profitability = route.total_revenue - route.total_cost
            route.margin_percent = route.profitability / route.total_revenue * 100 if route.total_revenue else 0.0

    @api.depends("total_weight", "total_volume", "vehicle_id.delivery_capacity_weight", "vehicle_id.delivery_capacity_volume")
    def _compute_utilization(self):
        for route in self:
            weight_capacity = route.vehicle_id.delivery_capacity_weight
            volume_capacity = route.vehicle_id.delivery_capacity_volume
            route.capacity_weight_utilization = route.total_weight / weight_capacity * 100 if weight_capacity else 0.0
            route.capacity_volume_utilization = route.total_volume / volume_capacity * 100 if volume_capacity else 0.0

    def _compute_public_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for route in self:
            token = route.tracking_token or ""
            route.public_url = "%s/delivery/track/%s" % (base_url, token) if token else False

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            vals.setdefault("company_id", self.env.company.id)
            if vals.get("name", "New") == "New":
                vals["name"] = sequence.next_by_code("delivery.route") or "New"
            vals.setdefault("tracking_token", secrets.token_urlsafe(24))
        records = super().create(vals_list)
        for record in records:
            self.env["delivery.event"].log_event("created", route=record)
        return records

    @api.constrains("warehouse_id", "vehicle_id", "driver_id", "company_id", "zone_id")
    def _check_company(self):
        for route in self:
            if route.warehouse_id.company_id and route.warehouse_id.company_id != route.company_id:
                raise ValidationError(_("Warehouse company must match route company."))
            if route.vehicle_id.company_id and route.vehicle_id.company_id != route.company_id:
                raise ValidationError(_("Vehicle company must match route company."))
            if route.driver_id.company_id and route.driver_id.company_id != route.company_id:
                raise ValidationError(_("Driver company must match route company."))
            if route.zone_id and route.zone_id.company_id != route.company_id:
                raise ValidationError(_("Delivery zone company must match route company."))

    @api.constrains("date", "line_ids")
    def _check_route_limits(self):
        for route in self:
            config = self.env["delivery.config"].sudo().get_company_config(route.company_id)
            if len(route.line_ids) > config.max_route_stops:
                raise ValidationError(_("Route %s exceeds the configured maximum of %s stops.") % (route.name, config.max_route_stops))

    def _validate_capacity(self):
        for route in self:
            vehicle = route.vehicle_id
            if not vehicle:
                continue
            if vehicle.delivery_capacity_weight and route.total_weight > vehicle.delivery_capacity_weight:
                raise ValidationError(_("Route weight %.2f kg exceeds vehicle capacity %.2f kg.") % (route.total_weight, vehicle.delivery_capacity_weight))
            if vehicle.delivery_capacity_volume and route.total_volume > vehicle.delivery_capacity_volume:
                raise ValidationError(_("Route volume %.2f m³ exceeds vehicle capacity %.2f m³.") % (route.total_volume, vehicle.delivery_capacity_volume))

    def _validate_driver_vehicle(self):
        for route in self:
            if not route.driver_id:
                raise ValidationError(_("A driver is required."))
            if not route.driver_id.delivery_available:
                raise ValidationError(_("The selected driver is not available for delivery."))
            if route.driver_id.delivery_license_expiry and route.driver_id.delivery_license_expiry < route.date:
                raise ValidationError(_("The selected driver's delivery license has expired."))
            if not route.vehicle_id:
                raise ValidationError(_("A vehicle is required."))
            if route.vehicle_id.delivery_status == "maintenance":
                raise ValidationError(_("The selected vehicle is under maintenance."))
            if route.vehicle_id.delivery_driver_license_required and not route.driver_id.delivery_license_number:
                raise ValidationError(_("The selected driver has no delivery license number."))

    def _validate_schedule(self):
        for route in self:
            if route.driver_id:
                schedule = self.env["delivery.driver.schedule"].search(
                    [("employee_id", "=", route.driver_id.id), ("date", "=", route.date)], limit=1
                )
                if schedule and not schedule.available:
                    raise ValidationError(_("The driver is not scheduled to work on %s.") % route.date)
                if schedule and route.estimated_duration > schedule.max_hours:
                    raise ValidationError(_("Estimated route duration exceeds the driver's maximum working hours."))

    def action_plan(self):
        for route in self:
            if route.state != "draft":
                raise UserError(_("Only draft routes can be planned."))
            if not route.line_ids:
                raise UserError(_("A route must contain at least one stop."))
            route._validate_capacity()
            route._validate_driver_vehicle()
            route._validate_schedule()
            route.line_ids.filtered(lambda line: line.status == "retry").write({"status": "pending"})
            route.state = "planned"
            self.env["delivery.event"].log_event("planned", route=route)
        return True

    def action_dispatch(self):
        for route in self:
            if route.state != "planned":
                raise UserError(_("Only planned routes can be dispatched."))
            route._validate_capacity()
            route._validate_driver_vehicle()
            route._validate_schedule()
            now = fields.Datetime.now()
            route.write({"state": "dispatched", "actual_start": route.actual_start or now})
            route.line_ids.filtered(lambda line: line.status in ("pending", "retry")).write({"status": "assigned"})
            route.vehicle_id.delivery_status = "assigned"
            self.env["delivery.event"].log_event("dispatched", route=route)
            route._notify_status("dispatched")
        return True

    def action_start(self):
        for route in self:
            if route.state != "dispatched":
                raise UserError(_("Only dispatched routes can start transit."))
            route.write({"state": "in_transit", "actual_start": route.actual_start or fields.Datetime.now()})
            route.line_ids.filtered(lambda line: line.status in ("assigned", "pending")).write({"status": "in_transit"})
            route.vehicle_id.delivery_status = "in_transit"
            self.env["delivery.event"].log_event("arrived", route=route, description=_("Route started."))
            route._notify_status("in_transit")
        return True

    def action_complete(self):
        for route in self:
            if route.state not in ("in_transit", "dispatched"):
                raise UserError(_("Route must be dispatched or in transit."))
            unresolved = route.line_ids.filtered(lambda line: line.status in ("pending", "assigned", "in_transit", "retry"))
            if unresolved:
                raise UserError(_("There are %s unresolved stops. Resolve them before completing the route.") % len(unresolved))
            delivered = route.line_ids.filtered(lambda line: line.status == "delivered")
            failed = route.line_ids.filtered(lambda line: line.status == "failed")
            partial = route.line_ids.filtered(lambda line: line.status == "partial")
            new_state = "done" if delivered and not failed and not partial else "partial" if delivered or partial else "failed"
            route.write({
                "state": new_state,
                "actual_end": fields.Datetime.now(),
                "actual_duration": route._get_actual_duration(),
            })
            route._create_default_costs()
            route.vehicle_id.delivery_status = "available"
            self.env["delivery.event"].log_event(new_state, route=route)
            route._notify_status(new_state)
        return True

    def action_cancel(self):
        for route in self:
            if route.state in ("done", "partial", "cancelled"):
                raise UserError(_("Completed or already cancelled routes cannot be cancelled."))
            route.state = "cancelled"
            route.line_ids.filtered(lambda line: line.status not in ("delivered", "failed", "cancelled")).write({"status": "cancelled"})
            if route.vehicle_id:
                route.vehicle_id.delivery_status = "available"
            if route.driver_id:
                self.env["delivery.event"].log_event("cancelled", route=route)
            route._notify_status("cancelled")
        return True

    def action_build_segments(self):
        Segment = self.env["delivery.route.segment"]
        for route in self:
            Segment.search([("route_id", "=", route.id)]).unlink()
            ordered = route.line_ids.sorted("sequence")
            previous = False
            sequence = 10
            for line in ordered:
                if previous:
                    Segment.create({
                        "route_id": route.id,
                        "sequence": sequence,
                        "from_line_id": previous.id,
                        "to_line_id": line.id,
                        "from_latitude": previous.latitude,
                        "from_longitude": previous.longitude,
                        "to_latitude": line.latitude,
                        "to_longitude": line.longitude,
                        "distance_km": line.distance_from_previous,
                        "duration_hours": line.duration_from_previous,
                        "provider": "heuristic",
                    })
                    sequence += 10
                previous = line
        return True

    def action_recompute_totals(self):
        self._compute_totals()
        self._compute_financials()
        return True

    def action_create_tracking_links(self):
        tracking_model = self.env["delivery.tracking.link"]
        for route in self:
            for line in route.line_ids.filtered(lambda line: line.partner_id):
                tracking_model.create_for_line(line)
        return True

    def action_open_plan_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "delivery.plan.route.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_warehouse_id": self.warehouse_id.id, "default_date": self.date, "default_route_id": self.id},
        }

    def action_open_optimize_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "delivery.optimize.route.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_route_id": self.id},
        }

    def action_open_dispatch_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "delivery.dispatch.route.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_route_id": self.id},
        }

    def action_print_route_manifest(self):
        return self.env.ref("delivery_fleet_pro.action_report_delivery_route_manifest").report_action(self)

    def action_print_pod_summary(self):
        return self.env.ref("delivery_fleet_pro.action_report_delivery_pod_summary").report_action(self)

    def action_print_failed_stops(self):
        return self.env.ref("delivery_fleet_pro.action_report_delivery_failed_stops").report_action(self)

    def action_print_cost_sheet(self):
        return self.env.ref("delivery_fleet_pro.action_report_delivery_route_cost").report_action(self)

    def action_print_driver_manifest(self):
        return self.env.ref("delivery_fleet_pro.action_report_delivery_driver_manifest").report_action(self)

    def _get_actual_duration(self):
        self.ensure_one()
        if not self.actual_start or not self.actual_end:
            return 0.0
        return max(0.0, (self.actual_end - self.actual_start).total_seconds() / 3600.0)

    def _create_default_costs(self):
        self.ensure_one()
        if self.cost_line_ids:
            return
        config = self.env["delivery.config"].sudo().get_company_config(self.company_id)
        distance = self.actual_distance or self.estimated_distance
        duration = self.actual_duration or self.estimated_duration
        fuel_liters = self.fuel_liters or (distance * config.default_fuel_consumption / 100.0)
        vals = []
        if fuel_liters:
            vals.append((0, 0, {
                "name": _("Fuel"),
                "cost_type": "fuel",
                "quantity": fuel_liters,
                "unit_cost": config.fuel_price_per_liter,
            }))
        if duration and config.driver_hourly_cost:
            vals.append((0, 0, {
                "name": _("Driver Time"),
                "cost_type": "driver",
                "quantity": duration,
                "unit_cost": config.driver_hourly_cost,
            }))
        if duration and config.vehicle_hourly_cost:
            vals.append((0, 0, {
                "name": _("Vehicle Time"),
                "cost_type": "vehicle",
                "quantity": duration,
                "unit_cost": config.vehicle_hourly_cost,
            }))
        if vals:
            self.write({"cost_line_ids": vals})

    def _notify_status(self, status):
        config = self.env["delivery.config"].sudo().get_company_config(self.company_id)
        if not config.customer_notifications:
            return
        template = self.env.ref("delivery_fleet_pro.mail_template_delivery_status", raise_if_not_found=False)
        for line in self.line_ids.filtered(lambda line: line.partner_id.email):
            if template:
                template.sudo().send_mail(line.id, force_send=True, email_values={"email_to": line.partner_id.email})
            else:
                self.env["mail.mail"].sudo().create({
                    "subject": _("Delivery update: %s") % self.name,
                    "body_html": _("<p>Your delivery status is now <strong>%s</strong>.</p>") % status.replace("_", " ").title(),
                    "email_to": line.partner_id.email,
                    "author_id": self.env.user.partner_id.id,
                }).send()

    @api.model
    def cron_create_retries(self):
        retries = self.env["delivery.retry"].search([("state", "=", "scheduled"), ("scheduled_date", "<=", fields.Date.today())])
        for retry in retries:
            try:
                retry.action_create_retry()
            except UserError:
                continue
        return True
