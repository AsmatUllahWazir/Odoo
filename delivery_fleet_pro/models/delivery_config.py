from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryConfig(models.Model):
    _name = "delivery.config"
    _description = "Delivery Fleet Configuration"
    _inherit = ["mail.thread"]
    _order = "company_id, id"

    name = fields.Char(required=True, default=lambda self: _("Delivery Configuration"), tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    default_fuel_consumption = fields.Float(
        string="Fuel Consumption (L/100 km)", default=12.0
    )
    fuel_price_per_liter = fields.Monetary(string="Fuel Price / Liter", default=0.0)
    driver_hourly_cost = fields.Monetary(string="Driver Hourly Cost", default=0.0)
    vehicle_hourly_cost = fields.Monetary(string="Vehicle Hourly Cost", default=0.0)
    loading_minutes = fields.Float(default=15.0)
    default_service_minutes = fields.Float(default=10.0)
    max_route_stops = fields.Integer(default=50)
    max_route_hours = fields.Float(default=10.0)
    late_tolerance_minutes = fields.Integer(default=15)
    otp_length = fields.Integer(default=6)
    otp_expiry_minutes = fields.Integer(default=30)
    tracking_enabled = fields.Boolean(default=True)
    customer_notifications = fields.Boolean(default=True)
    public_tracking_enabled = fields.Boolean(default=True)
    optimization_provider = fields.Selection(
        [
            ("heuristic", "Built-in Heuristic"),
            ("openrouteservice", "OpenRouteService"),
            ("google", "Google Maps Platform"),
        ],
        default="heuristic",
        required=True,
    )
    routing_api_key = fields.Char(string="Routing API Key")
    routing_base_url = fields.Char()
    geocoding_enabled = fields.Boolean(default=False)
    auto_create_retry = fields.Boolean(default=True)
    retry_delay_days = fields.Integer(default=1)
    notify_before_delivery = fields.Boolean(default=True)
    notification_lead_minutes = fields.Integer(default=60)
    allow_manual_distance = fields.Boolean(default=True)
    map_default_zoom = fields.Integer(default=12)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True)
    notes = fields.Text()

    _sql_constraints = [
        (
            "company_unique",
            "unique(company_id)",
            "Only one active delivery configuration is allowed per company.",
        ),
        (
            "positive_fuel",
            "CHECK(default_fuel_consumption >= 0)",
            "Fuel consumption cannot be negative.",
        ),
        (
            "positive_stops",
            "CHECK(max_route_stops > 0)",
            "Maximum route stops must be greater than zero.",
        ),
    ]

    @api.constrains("otp_length", "otp_expiry_minutes", "retry_delay_days")
    def _check_security_values(self):
        for record in self:
            if record.otp_length < 4 or record.otp_length > 10:
                raise ValidationError(_("OTP length must be between 4 and 10 digits."))
            if record.otp_expiry_minutes <= 0:
                raise ValidationError(_("OTP expiry must be greater than zero."))
            if record.retry_delay_days < 0:
                raise ValidationError(_("Retry delay cannot be negative."))

    @api.model
    def get_company_config(self, company=None):
        company = company or self.env.company
        config = self.search([("company_id", "=", company.id), ("active", "=", True)], limit=1)
        return config or self.create({"company_id": company.id, "name": _("Delivery Configuration")})

    @api.model
    def get_param(self, field_name, default=False, company=None):
        config = self.get_company_config(company=company)
        return getattr(config, field_name, default)
