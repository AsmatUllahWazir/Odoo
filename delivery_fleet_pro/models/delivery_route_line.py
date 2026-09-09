from datetime import timedelta
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError


class DeliveryRouteLine(models.Model):
    _name = "delivery.route.line"
    _description = "Delivery Route Stop"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "route_id, sequence, id"

    route_id = fields.Many2one("delivery.route", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one("res.company", related="route_id.company_id", store=True)
    sequence = fields.Integer(default=10, index=True)
    picking_id = fields.Many2one("stock.picking", required=True, ondelete="restrict", index=True)
    partner_id = fields.Many2one("res.partner", related="picking_id.partner_id", store=True, index=True)
    address = fields.Char(related="partner_id.contact_address", readonly=True)
    street = fields.Char(related="partner_id.street", readonly=True)
    street2 = fields.Char(related="partner_id.street2", readonly=True)
    city = fields.Char(related="partner_id.city", readonly=True)
    state_id = fields.Many2one("res.country.state", related="partner_id.state_id", readonly=True)
    zip = fields.Char(related="partner_id.zip", readonly=True)
    country_id = fields.Many2one("res.country", related="partner_id.country_id", readonly=True)
    phone = fields.Char(related="partner_id.phone", readonly=True)
    mobile = fields.Char(related="partner_id.mobile", readonly=True)
    email = fields.Char(related="partner_id.email", readonly=True)
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    date_from = fields.Datetime()
    date_to = fields.Datetime()
    preferred_from = fields.Float(related="partner_id.delivery_preferred_from", readonly=True)
    preferred_to = fields.Float(related="partner_id.delivery_preferred_to", readonly=True)
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("assigned", "Assigned"),
            ("in_transit", "In Transit"),
            ("arrived", "Arrived"),
            ("delivered", "Delivered"),
            ("partial", "Partial"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
            ("retry", "Retry Scheduled"),
        ],
        default="pending",
        required=True,
        tracking=True,
        index=True,
    )
    proof_id = fields.Many2one("delivery.proof", string="Proof of Delivery", copy=False)
    failure_id = fields.Many2one("delivery.failure", string="Failure", copy=False)
    retry_route_line_id = fields.Many2one("delivery.route.line", string="Created Retry Stop", copy=False)
    retry_date = fields.Date()
    package_ids = fields.One2many("delivery.package", "route_line_id", string="Packages")
    attempt_ids = fields.One2many("delivery.attempt", "route_line_id", string="Attempts")
    segment_from_ids = fields.One2many("delivery.route.segment", "from_line_id", string="Outgoing Segments")
    segment_to_ids = fields.One2many("delivery.route.segment", "to_line_id", string="Incoming Segments")
    package_count = fields.Integer(compute="_compute_package_count", store=True)
    weight = fields.Float()
    volume = fields.Float()
    delivered_weight = fields.Float()
    delivered_volume = fields.Float()
    revenue = fields.Monetary(compute="_compute_revenue", store=True)
    cost_total = fields.Monetary(compute="_compute_cost", store=True)
    currency_id = fields.Many2one("res.currency", related="route_id.currency_id", store=True)
    service_minutes = fields.Float(compute="_compute_service_minutes", store=True)
    arrival_time = fields.Datetime()
    departure_time = fields.Datetime()
    delivery_duration_minutes = fields.Float(compute="_compute_delivery_duration", store=True)
    distance_from_previous = fields.Float(string="Distance From Previous (km)")
    duration_from_previous = fields.Float(string="Duration From Previous (hours)")
    on_time = fields.Boolean(compute="_compute_on_time", store=True)
    late_minutes = fields.Float(compute="_compute_late", store=True)
    tracking_link_id = fields.Many2one("delivery.tracking.link", copy=False)
    notes = fields.Text()

    _sql_constraints = [
        ("sequence_positive", "CHECK(sequence >= 0)", "Sequence cannot be negative."),
        ("weight_positive", "CHECK(weight >= 0)", "Weight cannot be negative."),
        ("volume_positive", "CHECK(volume >= 0)", "Volume cannot be negative."),
    ]

    @api.depends("package_ids")
    def _compute_package_count(self):
        for line in self:
            line.package_count = len(line.package_ids)

    @api.depends("picking_id.sale_id.amount_total", "picking_id.sale_id.currency_id", "route_id.currency_id", "picking_id.sale_id.amount_untaxed")
    def _compute_revenue(self):
        for line in self:
            amount = line.picking_id.sale_id.amount_total if line.picking_id.sale_id else 0.0
            if line.picking_id.sale_id and line.picking_id.sale_id.currency_id != line.currency_id:
                amount = line.picking_id.sale_id.currency_id._convert(
                    amount,
                    line.currency_id,
                    line.route_id.company_id,
                    line.route_id.date or fields.Date.today(),
                )
            line.revenue = amount

    @api.depends("distance_from_previous", "duration_from_previous", "route_id.fuel_liters", "route_id.driver_hours", "route_id.vehicle_hours")
    def _compute_cost(self):
        for line in self:
            route = line.route_id
            config = self.env["delivery.config"].sudo().get_company_config(route.company_id)
            fuel = (line.distance_from_previous * config.default_fuel_consumption / 100.0) * config.fuel_price_per_liter
            driver = line.duration_from_previous * config.driver_hourly_cost
            vehicle = line.duration_from_previous * config.vehicle_hourly_cost
            line.cost_total = fuel + driver + vehicle

    @api.depends("route_id.service_type_id.default_service_minutes")
    def _compute_service_minutes(self):
        for line in self:
            line.service_minutes = line.route_id.service_type_id.default_service_minutes or 10.0

    @api.depends("arrival_time", "departure_time")
    def _compute_delivery_duration(self):
        for line in self:
            if line.arrival_time and line.departure_time:
                line.delivery_duration_minutes = max(0.0, (line.departure_time - line.arrival_time).total_seconds() / 60.0)
            else:
                line.delivery_duration_minutes = 0.0

    @api.depends("arrival_time", "date_from", "date_to", "preferred_from", "preferred_to")
    def _compute_on_time(self):
        for line in self:
            if not line.arrival_time:
                line.on_time = False
                continue
            if line.date_from and line.arrival_time < line.date_from:
                line.on_time = False
            elif line.date_to and line.arrival_time > line.date_to:
                line.on_time = False
            else:
                line.on_time = True

    @api.depends("arrival_time", "date_to")
    def _compute_late(self):
        for line in self:
            if line.arrival_time and line.date_to and line.arrival_time > line.date_to:
                line.late_minutes = (line.arrival_time - line.date_to).total_seconds() / 60.0
            else:
                line.late_minutes = 0.0

    @api.constrains("date_from", "date_to")
    def _check_window(self):
        for line in self:
            if line.date_from and line.date_to and line.date_from > line.date_to:
                raise ValidationError(_("The delivery time window start must be before the end."))

    @api.constrains("route_id", "picking_id")
    def _check_picking_company(self):
        for line in self:
            if line.picking_id.company_id != line.route_id.company_id:
                raise ValidationError(_("Picking company must match route company."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for line in records:
            if line.picking_id and not line.weight:
                line.weight = line._get_picking_weight()
            if line.picking_id and not line.volume:
                line.volume = line._get_picking_volume()
            self.env["delivery.event"].log_event("created", route=line.route_id, line=line)
        return records

    def _get_picking_weight(self):
        self.ensure_one()
        return sum(move.product_id.weight * move.product_uom_qty for move in self.picking_id.move_ids if move.product_id)

    def _get_picking_volume(self):
        self.ensure_one()
        return sum(move.product_id.volume * move.product_uom_qty for move in self.picking_id.move_ids if move.product_id)

    def action_mark_arrived(self):
        for line in self:
            if line.status not in ("assigned", "in_transit"):
                raise UserError(_("This stop cannot be marked arrived from its current status."))
            line.write({"status": "arrived", "arrival_time": fields.Datetime.now()})
            self.env["delivery.event"].log_event("arrived", route=line.route_id, line=line, source="driver")
        return True

    def action_mark_delivered(self):
        for line in self:
            if line.status in ("cancelled", "failed"):
                raise UserError(_("This stop cannot be marked delivered from its current status."))
            if line.route_id.state not in ("dispatched", "in_transit"):
                raise UserError(_("The route must be dispatched or in transit."))
            line.write({
                "status": "delivered",
                "arrival_time": line.arrival_time or fields.Datetime.now(),
                "departure_time": fields.Datetime.now(),
                "delivered_weight": line.weight,
                "delivered_volume": line.volume,
            })
            line._validate_required_pod()
            line._complete_picking_if_possible()
            self.env["delivery.event"].log_event("delivered", route=line.route_id, line=line, source="driver")
        return True

    def action_mark_partial(self):
        for line in self:
            if not line.route_id.service_type_id.allow_partial:
                raise UserError(_("Partial delivery is disabled for this service type."))
            line.write({"status": "partial", "arrival_time": line.arrival_time or fields.Datetime.now(), "departure_time": fields.Datetime.now()})
            self.env["delivery.event"].log_event("partial", route=line.route_id, line=line, source="driver")
        return True

    def action_open_failure_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "delivery.failure.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_route_line_id": self.id},
        }

    def action_open_pod_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "delivery.pod.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_route_line_id": self.id},
        }

    def _validate_required_pod(self):
        self.ensure_one()
        service = self.route_id.service_type_id
        if not service:
            return
        if service.requires_signature and not self.proof_id.signature:
            raise UserError(_("A signature is required before completing this delivery."))
        if service.requires_photo and not self.proof_id.photo:
            raise UserError(_("A delivery photo is required before completing this delivery."))
        if service.requires_otp and not self.proof_id.otp_verified:
            raise UserError(_("OTP verification is required before completing this delivery."))

    def _complete_picking_if_possible(self):
        self.ensure_one()
        picking = self.picking_id
        if picking.state in ("done", "cancel"):
            return
        if self.status == "delivered":
            try:
                if picking.state == "draft":
                    picking.action_confirm()
                if picking.state in ("confirmed", "waiting", "assigned"):
                    picking.action_assign()
                if picking.state == "assigned":
                    for move in picking.move_ids:
                        for move_line in move.move_line_ids:
                            if move_line.product_id.tracking == "none":
                                move_line.quantity = move_line.move_id.product_uom_qty
                    picking.button_validate()
            except Exception as error:
                self.message_post(body=_("Automatic picking validation was not completed: %s") % error)

    def action_create_tracking_link(self):
        for line in self:
            line.tracking_link_id = self.env["delivery.tracking.link"].create_for_line(line)
        return True
