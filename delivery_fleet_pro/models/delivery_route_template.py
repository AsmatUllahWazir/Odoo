from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class DeliveryRouteTemplate(models.Model):
    _name = "delivery.route.template"
    _description = "Delivery Route Template"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one("stock.warehouse", required=True)
    vehicle_id = fields.Many2one("fleet.vehicle")
    driver_id = fields.Many2one("hr.employee")
    weekday_monday = fields.Boolean()
    weekday_tuesday = fields.Boolean()
    weekday_wednesday = fields.Boolean()
    weekday_thursday = fields.Boolean()
    weekday_friday = fields.Boolean()
    weekday_saturday = fields.Boolean()
    weekday_sunday = fields.Boolean()
    start_hour = fields.Float(default=8.0)
    max_stops = fields.Integer(default=50)
    max_weight = fields.Float()
    max_volume = fields.Float()
    notes = fields.Text()

    @api.constrains("max_stops", "max_weight", "max_volume")
    def _check_limits(self):
        for rec in self:
            if rec.max_stops <= 0:
                raise ValidationError(_("Maximum stops must be greater than zero."))
            if rec.max_weight < 0 or rec.max_volume < 0:
                raise ValidationError(_("Route limits cannot be negative."))

    def applies_to_weekday(self, weekday):
        self.ensure_one()
        return bool(
            [
                self.weekday_monday,
                self.weekday_tuesday,
                self.weekday_wednesday,
                self.weekday_thursday,
                self.weekday_friday,
                self.weekday_saturday,
                self.weekday_sunday,
            ][weekday]
        )

    def action_create_route(self, date):
        self.ensure_one()
        date = fields.Date.to_date(date)
        if not self.applies_to_weekday(date.weekday()):
            raise UserError(_("This route template is not active for the selected weekday."))
        return self.env["delivery.route"].create(
            {
                "date": date,
                "company_id": self.company_id.id,
                "warehouse_id": self.warehouse_id.id,
                "vehicle_id": self.vehicle_id.id,
                "driver_id": self.driver_id.id,
                "template_id": self.id,
            }
        )
