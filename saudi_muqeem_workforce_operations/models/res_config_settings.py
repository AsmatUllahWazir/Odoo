from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    compliance_reminder_days = fields.Integer(string='Default Compliance Reminder Days', default=30, config_parameter='saudi_muqeem_workforce_operations.reminder_days')
    create_activities = fields.Boolean(string='Create HR Activities for Expiry', default=True, config_parameter='saudi_muqeem_workforce_operations.create_activities')
    auto_create_cases = fields.Boolean(string='Auto-create Compliance Cases', default=True, config_parameter='saudi_muqeem_workforce_operations.auto_create_cases')
    default_document_owner_id = fields.Many2one('res.users', string='Default Compliance Owner')
