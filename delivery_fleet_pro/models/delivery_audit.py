from odoo import api, fields, models


class DeliveryAudit(models.Model):
    _name = "delivery.audit"
    _description = "Delivery Audit Log"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True)
    model_name = fields.Char(index=True)
    record_id = fields.Integer(index=True)
    route_id = fields.Many2one("delivery.route", ondelete="set null")
    route_line_id = fields.Many2one("delivery.route.line", ondelete="set null")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    action = fields.Selection(
        [("create", "Create"), ("write", "Update"), ("state", "State Change"), ("dispatch", "Dispatch"), ("pod", "POD"), ("failure", "Failure"), ("retry", "Retry"), ("cancel", "Cancel")],
        required=True,
    )
    old_value = fields.Text()
    new_value = fields.Text()
    ip_address = fields.Char()
    user_agent = fields.Char()
    notes = fields.Text()

    @api.model
    def log(self, action, record, old_value=False, new_value=False, route=None, line=None, notes=False):
        return self.create({
            "name": "%s: %s" % (action.title(), record.display_name),
            "model_name": record._name,
            "record_id": record.id,
            "route_id": route.id if route else False,
            "route_line_id": line.id if line else False,
            "action": action,
            "old_value": old_value,
            "new_value": new_value,
            "notes": notes,
        })
