from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    delivery_tracking_enabled = fields.Boolean(related="delivery_config_id.tracking_enabled", readonly=False)
    delivery_public_tracking_enabled = fields.Boolean(related="delivery_config_id.public_tracking_enabled", readonly=False)
    delivery_customer_notifications = fields.Boolean(related="delivery_config_id.customer_notifications", readonly=False)
    delivery_optimization_provider = fields.Selection(related="delivery_config_id.optimization_provider", readonly=False)
    delivery_routing_api_key = fields.Char(related="delivery_config_id.routing_api_key", readonly=False)
    delivery_routing_base_url = fields.Char(related="delivery_config_id.routing_base_url", readonly=False)
    delivery_config_id = fields.Many2one("delivery.config", compute="_compute_delivery_config", readonly=False)

    @api.depends("company_id")
    def _compute_delivery_config(self):
        config_model = self.env["delivery.config"].sudo()
        for settings in self:
            settings.delivery_config_id = config_model.get_company_config(settings.company_id or self.env.company)

    def set_values(self):
        super().set_values()
        self.delivery_config_id.sudo().write({
            "tracking_enabled": self.delivery_tracking_enabled,
            "public_tracking_enabled": self.delivery_public_tracking_enabled,
            "customer_notifications": self.delivery_customer_notifications,
            "optimization_provider": self.delivery_optimization_provider,
            "routing_api_key": self.delivery_routing_api_key,
            "routing_base_url": self.delivery_routing_base_url,
        })
