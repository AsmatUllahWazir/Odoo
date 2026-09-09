from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryVehicleLog(models.Model):
    _name = "delivery.vehicle.log"
    _description = "Delivery Vehicle Log"
    _order = "date desc, id desc"

    name = fields.Char(required=True)
    vehicle_id = fields.Many2one("fleet.vehicle", required=True, ondelete="cascade")
    route_id = fields.Many2one("delivery.route", ondelete="set null")
    date = fields.Datetime(default=fields.Datetime.now, required=True)
    log_type = fields.Selection(
        [("fuel", "Fuel"), ("odometer", "Odometer"), ("maintenance", "Maintenance"), ("incident", "Incident"), ("note", "Note")],
        required=True,
    )
    liters = fields.Float()
    unit_price = fields.Monetary()
    amount = fields.Monetary(compute="_compute_amount", store=True)
    odometer = fields.Float()
    notes = fields.Text()
    currency_id = fields.Many2one("res.currency", related="vehicle_id.company_id.currency_id", store=True)

    @api.depends("liters", "unit_price")
    def _compute_amount(self):
        for log in self:
            log.amount = log.liters * log.unit_price

    @api.constrains("liters", "unit_price", "odometer")
    def _check_values(self):
        for log in self:
            if log.liters < 0 or log.unit_price < 0 or log.odometer < 0:
                raise ValidationError(_("Vehicle log numeric values cannot be negative."))
