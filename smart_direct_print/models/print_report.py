# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SmartPrintReport(models.Model):
    """
    Print Report Configuration Model

    Adds direct-print configuration around ir.actions.report.
    """
    _name = 'smart.print.report'
    _description = 'Smart Print Report Configuration'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Configuration Name',
        required=True,
        tracking=True,
        help='A descriptive name for this configuration'
    )
    report_id = fields.Many2one(
        'ir.actions.report',
        string='Report',
        required=True,
        tracking=True,
        help='The report this configuration applies to'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Enable or disable this configuration'
    )

    # Direct Print Settings
    direct_print_enabled = fields.Boolean(
        string='Direct Printing Enabled',
        default=False,
        tracking=True,
        help='Enable direct printing for this report'
    )
    default_printer_id = fields.Many2one(
        'smart.printer',
        string='Default Printer',
        help='Default printer to use for this report'
    )
    default_rule_id = fields.Many2one(
        'smart.print.rule',
        string='Default Rule',
        help='Default rule to use for printer selection'
    )
    number_of_copies = fields.Integer(
        string='Default Copies',
        default=1,
        min=1,
        max=999,
        tracking=True,
        help='Default number of copies'
    )
    supported_format = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('esc_pos', 'ESC/POS'),
        ('raw', 'RAW'),
    ], string='Output Format', default='pdf', tracking=True)

    # Automatic Printing
    auto_print_enabled = fields.Boolean(
        string='Auto Print Enabled',
        default=False,
        tracking=True,
        help='Enable automatic printing for this report'
    )
    auto_print_scenario_id = fields.Many2one(
        'smart.print.scenario',
        string='Auto Print Scenario',
        help='Scenario to use for automatic printing'
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help='Company this configuration belongs to'
    )

    _sql_constraints = [
        ('unique_report_company', 'unique(report_id, company_id)',
         'Report configuration must be unique per company!')
    ]

    @api.constrains('default_printer_id', 'default_rule_id')
    def _check_printer_consistency(self):
        """Check that printer and rule are consistent."""
        for config in self:
            if config.default_printer_id and config.default_rule_id:
                if config.default_printer_id != config.default_rule_id.printer_id:
                    raise ValidationError(_(
                        'Default printer and rule printer must match'
                    ))

    @api.model
    def get_report_config(self, report_id):
        """
        Get configuration for a report.

        Args:
            report_id (int): ID of the report

        Returns:
            smart.print.report: The configuration or None
        """
        if not report_id:
            return None

        config = self.search([
            ('report_id', '=', report_id),
            '|',
            ('company_id', '=', self.env.company.id),
            ('company_id', '=', False)
        ], limit=1)

        if config and config.active:
            return config

        return None

    def enable_direct_print(self):
        """Enable direct printing for this report."""
        self.ensure_one()
        self.write({
            'direct_print_enabled': True
        })

    def disable_direct_print(self):
        """Disable direct printing for this report."""
        self.ensure_one()
        self.write({
            'direct_print_enabled': False
        })

    def enable_auto_print(self):
        """Enable automatic printing for this report."""
        self.ensure_one()
        self.write({
            'auto_print_enabled': True
        })

    def disable_auto_print(self):
        """Disable automatic printing for this report."""
        self.ensure_one()
        self.write({
            'auto_print_enabled': False
        })
        