from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryRouteCharge(models.Model):
    _name = "delivery.route.charge"
    _description = "Delivery Route Charge"
    _order = "route_id, sequence, id"

    route_id = fields.Many2one("delivery.route", required=True, ondelete="cascade", index=True)
    route_line_id = fields.Many2one("delivery.route.line", ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    charge_type = fields.Selection(
        [("delivery", "Delivery Fee"), ("fuel_surcharge", "Fuel Surcharge"), ("distance", "Distance Fee"), ("time", "Time Fee"), ("waiting", "Waiting Fee"), ("other", "Other")],
        required=True,
    )
    quantity = fields.Float(default=1.0)
    unit_price = fields.Monetary()
    amount = fields.Monetary(compute="_compute_amount", store=True)
    currency_id = fields.Many2one("res.currency", related="route_id.currency_id", store=True)
    invoice_id = fields.Many2one("account.move", readonly=True)
    invoiced = fields.Boolean(compute="_compute_invoiced", store=True)
    notes = fields.Text()

    @api.depends("quantity", "unit_price")
    def _compute_amount(self):
        for charge in self:
            charge.amount = charge.quantity * charge.unit_price

    @api.depends("invoice_id.state")
    def _compute_invoiced(self):
        for charge in self:
            charge.invoiced = bool(charge.invoice_id and charge.invoice_id.state != "cancel")

    @api.constrains("quantity", "unit_price")
    def _check_amounts(self):
        for charge in self:
            if charge.quantity < 0 or charge.unit_price < 0:
                raise ValidationError(_("Charge quantity and unit price cannot be negative."))
