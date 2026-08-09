# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    """
    User Model Extension

    Adds printer preferences and workstation configuration to users.
    """
    _inherit = 'res.users'

    # Printer Preferences
    default_printer_id = fields.Many2one(
        'smart.printer',
        string='Default Printer',
        help='Default printer for this user'
    )
    printer_rule_ids = fields.Many2many(
        'smart.print.rule',
        string='Printer Rules',
        help='Additional printer rules for this user'
    )

    # Workstation
    workstation_name = fields.Char(
        string='Workstation Name',
        help='Name of the workstation for printer routing'
    )

    # Print Preferences
    auto_print_enabled = fields.Boolean(
        string='Automatic Printing Enabled',
        default=True,
        help='Enable automatic printing for this user'
    )
    print_preference = fields.Selection([
        ('direct', 'Direct Print'),
        ('download', 'Download PDF'),
        ('ask', 'Ask Each Time')
    ], string='Print Preference', default='ask',
        help='Preferred printing method')

    # Additional
    show_print_notifications = fields.Boolean(
        string='Show Print Notifications',
        default=True,
        help='Show notifications for print jobs'
    )

    @api.model
    def get_user_printer(self, report_id=None):
        """
        Get the default printer for the current user.

        Args:
            report_id (int): Report ID for context

        Returns:
            smart.printer: The user's default printer or None
        """
        user = self.env.user

        # Check user's default printer
        if user.default_printer_id:
            return user.default_printer_id

        # Check report configuration
        if report_id:
            report_config = self.env['smart.print.report'].get_report_config(report_id)
            if report_config and report_config.default_printer_id:
                return report_config.default_printer_id

        # Check company default
        company_printer = self.env['smart.printer'].search([
            ('company_id', '=', user.company_id.id),
            ('active', '=', True)
        ], limit=1)
        if company_printer:
            return company_printer

        return None

    @api.model
    def get_workstation(self):
        """
        Get the current workstation name.

        Returns:
            str: Workstation name or empty string
        """
        return self.env.user.workstation_name or ''

    @api.model
    def get_print_preference(self):
        """
        Get the user's print preference.

        Returns:
            str: Print preference ('direct', 'download', 'ask')
        """
        return self.env.user.print_preference or 'ask'

    def action_set_default_printer(self, printer_id):
        """
        Set default printer for user.

        Args:
            printer_id (int): Printer ID

        Returns:
            bool: True if successful
        """
        self.ensure_one()

        printer = self.env['smart.printer'].browse(printer_id)
        if not printer.exists():
            raise ValidationError(_('Printer does not exist'))

        self.write({'default_printer_id': printer_id})

        return True

    def action_clear_default_printer(self):
        """Clear the user's default printer."""
        self.ensure_one()
        self.write({'default_printer_id': False})

    def action_get_available_printers(self):
        """
        Get available printers for the user.

        Returns:
            smart.printer: Domain of available printers
        """
        return self.env['smart.printer'].search([
            ('active', '=', True),
            '|',
            ('user_ids', '=', False),
            ('user_ids', 'in', [self.id])
        ])
