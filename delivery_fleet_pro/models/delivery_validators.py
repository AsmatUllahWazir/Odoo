from odoo import api, models, _
from odoo.exceptions import ValidationError


class DeliveryValidationService(models.AbstractModel):
    _name = "delivery.validation.service"
    _description = "Delivery Validation Service"

    @api.model
    def validate_route(self, route, strict=True):
        messages = []
        if not route.line_ids:
            messages.append(_("Route has no stops."))
        if not route.driver_id:
            messages.append(_("Route has no driver."))
        if not route.vehicle_id:
            messages.append(_("Route has no vehicle."))
        if route.vehicle_id:
            if route.vehicle_id.delivery_capacity_weight and route.total_weight > route.vehicle_id.delivery_capacity_weight:
                messages.append(_("Weight capacity exceeded."))
            if route.vehicle_id.delivery_capacity_volume and route.total_volume > route.vehicle_id.delivery_capacity_volume:
                messages.append(_("Volume capacity exceeded."))
            if route.vehicle_id.delivery_capacity_packages and route.total_packages > route.vehicle_id.delivery_capacity_packages:
                messages.append(_("Package capacity exceeded."))
        for line in route.line_ids:
            if not line.partner_id:
                messages.append(_("Stop %s has no customer.") % line.display_name)
            if line.date_from and line.date_to and line.date_from > line.date_to:
                messages.append(_("Stop %s has an invalid time window.") % line.display_name)
            if not line.latitude and not line.longitude:
                messages.append(_("Stop %s has no GPS coordinates.") % line.display_name)
        if strict and messages:
            raise ValidationError("\n".join(messages))
        return messages

    @api.model
    def validate_driver(self, driver, date=None):
        messages = []
        if not driver:
            return [_('Driver is required.')]
        if not driver.delivery_available:
            messages.append(_("Driver is marked unavailable."))
        if date and driver.delivery_license_expiry and driver.delivery_license_expiry < date:
            messages.append(_("Driver license is expired."))
        if driver.delivery_max_hours <= 0:
            messages.append(_("Driver maximum hours are not configured."))
        return messages

    @api.model
    def validate_vehicle(self, vehicle):
        messages = []
        if not vehicle:
            return [_('Vehicle is required.')]
        if vehicle.delivery_status == "maintenance":
            messages.append(_("Vehicle is under maintenance."))
        if vehicle.delivery_capacity_weight < 0:
            messages.append(_("Vehicle weight capacity is invalid."))
        if vehicle.delivery_capacity_volume < 0:
            messages.append(_("Vehicle volume capacity is invalid."))
        if vehicle.delivery_capacity_packages < 0:
            messages.append(_("Vehicle package capacity is invalid."))
        return messages
