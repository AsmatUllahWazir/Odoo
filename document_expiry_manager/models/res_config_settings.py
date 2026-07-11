# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    document_expiry_default_warning_days = fields.Integer(
        string='Default Warning Window (days)',
        config_parameter='document_expiry_manager.default_warning_days',
        default=30,
        help="Default number of days before expiry at which new documents are "
             "flagged as 'Expiring Soon' if their type does not define its own value.")
    document_expiry_default_reminder_schedule = fields.Char(
        string='Default Reminder Schedule',
        config_parameter='document_expiry_manager.default_reminder_schedule',
        default='30,15,7,1',
        help="Default comma separated reminder day thresholds used for new documents.")
