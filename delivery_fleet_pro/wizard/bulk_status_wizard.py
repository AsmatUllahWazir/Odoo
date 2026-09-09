from odoo import fields, models, _
from odoo.exceptions import UserError


class DeliveryBulkStatusWizard(models.TransientModel):
    _name = "delivery.bulk.status.wizard"
    _description = "Bulk Delivery Status Update"

    line_ids = fields.Many2many("delivery.route.line", required=True)
    target_status = fields.Selection(
        [("assigned", "Assigned"), ("in_transit", "In Transit"), ("arrived", "Arrived"), ("delivered", "Delivered"), ("partial", "Partial"), ("cancelled", "Cancelled")],
        required=True,
    )
    note = fields.Text()

    def action_apply(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("Select at least one stop."))
        for line in self.line_ids:
            if self.target_status == "delivered":
                line.action_mark_delivered()
            elif self.target_status == "partial":
                line.action_mark_partial()
            else:
                line.status = self.target_status
            if self.note:
                line.message_post(body=self.note)
        return True
