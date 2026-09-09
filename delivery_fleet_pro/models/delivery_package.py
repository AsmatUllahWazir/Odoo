from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryPackage(models.Model):
    _name = "delivery.package"
    _description = "Delivery Package"
    _order = "route_line_id, sequence, id"

    name = fields.Char(required=True, copy=False)
    route_line_id = fields.Many2one("delivery.route.line", required=True, ondelete="cascade")
    picking_id = fields.Many2one("stock.picking", related="route_line_id.picking_id", store=True)
    sequence = fields.Integer(default=10)
    package_type = fields.Selection(
        [("box", "Box"), ("pallet", "Pallet"), ("envelope", "Envelope"), ("bag", "Bag"), ("other", "Other")],
        default="box",
        required=True,
    )
    quantity = fields.Float(default=1.0)
    weight = fields.Float()
    volume = fields.Float()
    barcode = fields.Char(index=True)
    fragile = fields.Boolean()
    temperature_controlled = fields.Boolean()
    collected = fields.Boolean()
    delivered = fields.Boolean()
    notes = fields.Text()

    @api.constrains("quantity", "weight", "volume")
    def _check_measurements(self):
        for package in self:
            if package.quantity <= 0:
                raise ValidationError(_("Package quantity must be greater than zero."))
            if package.weight < 0 or package.volume < 0:
                raise ValidationError(_("Package weight and volume cannot be negative."))
