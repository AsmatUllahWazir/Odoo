from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryDispatchRouteWizard(models.TransientModel):
    _name = "delivery.dispatch.route.wizard"
    _description = "Dispatch Delivery Route"

    route_id = fields.Many2one("delivery.route", required=True)
    confirm_driver = fields.Boolean(default=True)
    confirm_vehicle = fields.Boolean(default=True)
    send_customer_notifications = fields.Boolean(default=True)
    create_tracking_links = fields.Boolean(default=True)
    notes = fields.Text()

    @api.onchange("route_id")
    def _onchange_route(self):
        if self.route_id:
            self.confirm_driver = bool(self.route_id.driver_id)
            self.confirm_vehicle = bool(self.route_id.vehicle_id)

    def action_dispatch(self):
        self.ensure_one()
        if self.route_id.state != "planned":
            raise UserError(_("The route must be planned before dispatch."))
        if self.confirm_driver and not self.route_id.driver_id:
            raise UserError(_("A driver must be assigned before dispatch."))
        if self.confirm_vehicle and not self.route_id.vehicle_id:
            raise UserError(_("A vehicle must be assigned before dispatch."))
        self.route_id.action_dispatch()
        if self.create_tracking_links:
            self.route_id.action_create_tracking_links()
        if not self.send_customer_notifications:
            return True
        self.route_id.message_post(body=_("Route dispatched. Customer tracking links were generated."))
        return True
