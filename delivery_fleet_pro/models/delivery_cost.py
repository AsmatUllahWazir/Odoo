from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryRouteCost(models.Model):
    _name = "delivery.route.cost"
    _description = "Delivery Route Cost"
    _order = "route_id, sequence, id"

    route_id = fields.Many2one("delivery.route", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    cost_type = fields.Selection(
        [
            ("fuel", "Fuel"),
            ("driver", "Driver"),
            ("vehicle", "Vehicle"),
            ("toll", "Toll"),
            ("maintenance", "Maintenance"),
            ("parking", "Parking"),
            ("outsourced", "Outsourced"),
            ("other", "Other"),
        ],
        required=True,
    )
    quantity = fields.Float(default=1.0)
    unit_cost = fields.Monetary()
    amount = fields.Monetary(compute="_compute_amount", store=True)
    currency_id = fields.Many2one("res.currency", related="route_id.currency_id", store=True)
    vendor_id = fields.Many2one("res.partner")
    analytic_account_id = fields.Many2one("account.analytic.account")
    account_move_id = fields.Many2one("account.move", readonly=True)
    notes = fields.Text()

    @api.depends("quantity", "unit_cost")
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.unit_cost

    @api.constrains("quantity", "unit_cost")
    def _check_cost_values(self):
        for line in self:
            if line.quantity < 0 or line.unit_cost < 0:
                raise ValidationError(_("Cost quantity and unit cost cannot be negative."))

    def action_open_account_move(self):
        self.ensure_one()
        if not self.account_move_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.account_move_id.id,
        }
