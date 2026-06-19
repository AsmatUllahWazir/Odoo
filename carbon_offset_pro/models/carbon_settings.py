from odoo import models, fields, api, _


class CarbonConfigSettings(models.TransientModel):
    _name = 'carbon.config.settings'
    _description = 'Carbon Governance Settings'

    # General Settings
    carbon_governance_enabled = fields.Boolean(
        string='Enable Carbon Governance',
        default=True
    )

    # Auto-Submit Settings
    auto_submit_records = fields.Boolean(
        string='Auto-Submit Carbon Records',
        default=False
    )

    # Maintenance Integration
    maintenance_integration_enabled = fields.Boolean(
        string='Enable Maintenance Integration',
        default=False
    )

    # Using integer fields for IDs to avoid Many2one issues in TransientModel
    default_maintenance_scope_id = fields.Integer(
        string='Maintenance Default Scope ID'
    )
    default_maintenance_category_id = fields.Integer(
        string='Maintenance Default Category ID'
    )
    default_maintenance_factor_id = fields.Integer(
        string='Maintenance Default Factor ID'
    )

    # Display fields for Many2one (readonly)
    default_maintenance_scope = fields.Many2one(
        'carbon.scope',
        string='Maintenance Default Scope',
        compute='_compute_maintenance_scope',
        readonly=True,
        store=False
    )
    default_maintenance_category = fields.Many2one(
        'carbon.category',
        string='Maintenance Default Category',
        compute='_compute_maintenance_category',
        readonly=True,
        store=False
    )
    default_maintenance_factor = fields.Many2one(
        'carbon.emission.factor',
        string='Maintenance Default Factor',
        compute='_compute_maintenance_factor',
        readonly=True,
        store=False
    )

    auto_submit_maintenance_records = fields.Boolean(
        string='Auto-Submit Maintenance Records',
        default=False
    )

    # Future Integrations
    enable_purchase_integration = fields.Boolean(
        string='Enable Purchase Integration',
        default=False
    )
    enable_fleet_integration = fields.Boolean(
        string='Enable Fleet Integration',
        default=False
    )
    enable_project_integration = fields.Boolean(
        string='Enable Project Integration',
        default=False
    )

    def _compute_maintenance_scope(self):
        for record in self:
            if record.default_maintenance_scope_id:
                record.default_maintenance_scope = self.env['carbon.scope'].browse(record.default_maintenance_scope_id)
            else:
                record.default_maintenance_scope = False

    def _compute_maintenance_category(self):
        for record in self:
            if record.default_maintenance_category_id:
                record.default_maintenance_category = self.env['carbon.category'].browse(
                    record.default_maintenance_category_id)
            else:
                record.default_maintenance_category = False

    def _compute_maintenance_factor(self):
        for record in self:
            if record.default_maintenance_factor_id:
                record.default_maintenance_factor = self.env['carbon.emission.factor'].browse(
                    record.default_maintenance_factor_id)
            else:
                record.default_maintenance_factor = False

    @api.model
    def _get_settings(self):
        """Get settings from config parameters"""
        config = self.env['ir.config_parameter'].sudo()

        def get_int_param(key, default=0):
            try:
                return int(config.get_param(key, default))
            except (ValueError, TypeError):
                return default

        def get_bool_param(key, default=False):
            return config.get_param(key, str(default)) == 'True'

        return {
            'carbon_governance_enabled': get_bool_param('carbon_offset_pro.governance_enabled', True),
            'auto_submit_records': get_bool_param('carbon_offset_pro.auto_submit', False),
            'maintenance_integration_enabled': get_bool_param('carbon_offset_pro.maintenance_integration_enabled',
                                                              False),
            'default_maintenance_scope_id': get_int_param('carbon_offset_pro.default_maintenance_scope_id'),
            'default_maintenance_category_id': get_int_param('carbon_offset_pro.default_maintenance_category_id'),
            'default_maintenance_factor_id': get_int_param('carbon_offset_pro.default_maintenance_factor_id'),
            'auto_submit_maintenance_records': get_bool_param('carbon_offset_pro.auto_submit_maintenance', False),
            'enable_purchase_integration': get_bool_param('carbon_offset_pro.enable_purchase_integration', False),
            'enable_fleet_integration': get_bool_param('carbon_offset_pro.enable_fleet_integration', False),
            'enable_project_integration': get_bool_param('carbon_offset_pro.enable_project_integration', False),
        }

    @api.model
    def default_get(self, fields_list):
        """Load settings from config parameters"""
        defaults = super().default_get(fields_list)
        settings = self._get_settings()

        for field in fields_list:
            if field in settings:
                defaults[field] = settings[field]

        return defaults

    def action_save(self):
        """Save settings to config parameters"""
        config = self.env['ir.config_parameter'].sudo()

        config.set_param('carbon_offset_pro.governance_enabled', str(self.carbon_governance_enabled))
        config.set_param('carbon_offset_pro.auto_submit', str(self.auto_submit_records))
        config.set_param('carbon_offset_pro.maintenance_integration_enabled', str(self.maintenance_integration_enabled))
        config.set_param('carbon_offset_pro.default_maintenance_scope_id', str(self.default_maintenance_scope_id or 0))
        config.set_param('carbon_offset_pro.default_maintenance_category_id',
                         str(self.default_maintenance_category_id or 0))
        config.set_param('carbon_offset_pro.default_maintenance_factor_id',
                         str(self.default_maintenance_factor_id or 0))
        config.set_param('carbon_offset_pro.auto_submit_maintenance', str(self.auto_submit_maintenance_records))
        config.set_param('carbon_offset_pro.enable_purchase_integration', str(self.enable_purchase_integration))
        config.set_param('carbon_offset_pro.enable_fleet_integration', str(self.enable_fleet_integration))
        config.set_param('carbon_offset_pro.enable_project_integration', str(self.enable_project_integration))

        return {
            'type': 'ir.actions.act_window_close',
        }

    @api.model
    def get_settings(self):
        """Public method to get settings for other models"""
        return self._get_settings()
    