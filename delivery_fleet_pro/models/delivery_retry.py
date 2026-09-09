from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryRetry(models.Model):
    _name = "delivery.retry"
    _description = "Delivery Retry Schedule"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "scheduled_date, id"

    name = fields.Char(required=True, copy=False, default="New")
    company_id = fields.Many2one("res.company", related="original_line_id.route_id.company_id", store=True)
    original_line_id = fields.Many2one("delivery.route.line", required=True, ondelete="restrict")
    retry_line_id = fields.Many2one("delivery.route.line", readonly=True, copy=False)
    customer_id = fields.Many2one("res.partner", related="original_line_id.partner_id", store=True)
    picking_id = fields.Many2one("stock.picking", related="original_line_id.picking_id", store=True)
    scheduled_date = fields.Date(required=True)
    attempt_number = fields.Integer(default=1)
    reason_id = fields.Many2one("delivery.failure", required=True)
    state = fields.Selection(
        [("scheduled", "Scheduled"), ("created", "Retry Created"), ("cancelled", "Cancelled")],
        default="scheduled",
        required=True,
        tracking=True,
    )
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("delivery.retry") or "New"
        return super().create(vals_list)

    def action_create_retry(self):
        for retry in self:
            if retry.state != "scheduled":
                raise UserError(_("Only scheduled retries can be created."))
            source = retry.original_line_id
            route = self.env["delivery.route"].search(
                [
                    ("date", "=", retry.scheduled_date),
                    ("warehouse_id", "=", source.route_id.warehouse_id.id),
                    ("company_id", "=", source.route_id.company_id.id),
                    ("state", "in", ["draft", "planned"]),
                ],
                limit=1,
            )
            if not route:
                route = self.env["delivery.route"].create(
                    {
                        "date": retry.scheduled_date,
                        "warehouse_id": source.route_id.warehouse_id.id,
                        "vehicle_id": source.route_id.vehicle_id.id,
                        "driver_id": source.route_id.driver_id.id,
                    }
                )
            new_line = self.env["delivery.route.line"].create(
                {
                    "route_id": route.id,
                    "picking_id": source.picking_id.id,
                    "sequence": max(route.line_ids.mapped("sequence") or [0]) + 10,
                    "date_from": source.date_from,
                    "date_to": source.date_to,
                    "weight": source.weight,
                    "volume": source.volume,
                    "status": "retry",
                    "notes": _("Retry attempt %s created from failed stop %s.")
                    % (retry.attempt_number + 1, source.display_name),
                }
            )
            retry.write({"retry_line_id": new_line.id, "state": "created"})
            source.write({"retry_route_line_id": new_line.id, "retry_date": retry.scheduled_date, "status": "retry"})
        return True
