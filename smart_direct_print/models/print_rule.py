# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SmartPrintRule(models.Model):
    """
    Print Rule Model

    Controls printer selection based on various criteria.
    Rules are evaluated in priority order.
    """
    _name = 'smart.print.rule'
    _description = 'Smart Print Rule'
    _order = 'priority desc, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Rule Name',
        required=True,
        tracking=True,
        help='A descriptive name for this rule'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Enable or disable this rule'
    )
    priority = fields.Integer(
        string='Priority',
        default=10,
        tracking=True,
        help='Higher priority means the rule is evaluated first'
    )

    # Rule Conditions
    user_id = fields.Many2one(
        'res.users',
        string='User',
        help='Apply this rule only for this user'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        help='Apply this rule only for this company'
    )
    workstation_name = fields.Char(
        string='Workstation',
        help='Apply this rule only for this workstation'
    )
    report_id = fields.Many2one(
        'ir.actions.report',
        string='Report',
        help='Apply this rule only for this report'
    )
    model = fields.Char(
        string='Model',
        help='Apply this rule only for this model (e.g., sale.order)'
    )
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Carrier',
        help='Apply this rule only for this carrier'
    )
    document_type = fields.Char(
        string='Document Type',
        help='Apply this rule only for this document type'
    )
    domain_filter = fields.Text(
        string='Domain Filter',
        help='Additional domain filter for the document records\n'
             'Example: [(\'state\', \'=\', \'confirmed\')]'
    )

    # Rule Action
    printer_id = fields.Many2one(
        'smart.printer',
        string='Printer',
        required=True,
        tracking=True,
        help='Printer to use when this rule matches'
    )
    copies = fields.Integer(
        string='Copies',
        default=1,
        min=1,
        max=999,
        tracking=True,
        help='Number of copies to print'
    )

    # Additional
    apply_order = fields.Integer(
        string='Apply Order',
        default=0,
        help='Order within same priority group'
    )
    description = fields.Text(
        string='Description',
        help='Additional notes about this rule'
    )

    _sql_constraints = [
        ('unique_name_company', 'unique(name, company_id)',
         'Rule name must be unique per company!')
    ]

    @api.constrains('domain_filter')
    def _check_domain_filter(self):
        """Validate the domain filter expression."""
        for rule in self:
            if rule.domain_filter:
                try:
                    # Test parse the domain
                    eval(rule.domain_filter)
                except Exception as e:
                    raise ValidationError(_(
                        'Invalid domain filter expression: %s'
                    ) % str(e))

    @api.constrains('user_id', 'company_id', 'workstation_name')
    def _check_condition_completeness(self):
        """Check that at least one condition is set."""
        for rule in self:
            conditions = [
                rule.user_id,
                rule.company_id,
                rule.workstation_name,
                rule.report_id,
                rule.model,
                rule.carrier_id,
                rule.document_type,
                rule.domain_filter,
            ]
            if not any(conditions):
                raise ValidationError(_(
                    'At least one condition must be set for the rule'
                ))

    def evaluate_rule(self, document_info):
        """
        Evaluate if this rule applies to the given document info.

        Args:
            document_info (dict): Document information containing:
                - user: res.users record
                - company: res.company record
                - workstation: str
                - report: ir.actions.report record
                - model: str
                - carrier: delivery.carrier record
                - doc_type: str
                - record: record instance

        Returns:
            bool: True if the rule applies
        """
        self.ensure_one()

        if not self.active:
            return False

        # Check user
        if self.user_id and self.user_id != document_info.get('user'):
            return False

        # Check company
        if self.company_id and self.company_id != document_info.get('company'):
            return False

        # Check workstation
        if self.workstation_name and self.workstation_name != document_info.get('workstation'):
            return False

        # Check report
        if self.report_id and self.report_id != document_info.get('report'):
            return False

        # Check model
        if self.model and self.model != document_info.get('model'):
            return False

        # Check carrier
        if self.carrier_id and self.carrier_id != document_info.get('carrier'):
            return False

        # Check document type
        if self.document_type and self.document_type != document_info.get('doc_type'):
            return False

        # Check domain filter
        if self.domain_filter:
            try:
                domain = eval(self.domain_filter)
                record = document_info.get('record')
                if record and not self._check_domain(record, domain):
                    return False
            except Exception as e:
                _logger.warning(f"Domain filter evaluation failed: {e}")
                return False

        return True

    def _check_domain(self, record, domain):
        """Check if a record matches a domain."""
        if not record:
            return True

        # Use Odoo's domain evaluation
        try:
            return bool(record.filtered_domain(domain))
        except Exception:
            return False

    def action_duplicate(self):
        """
        Duplicate this rule.

        Returns:
            dict: Action to create a new rule with the same values
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.print.rule',
            'view_mode': 'form',
            'view_id': self.env.ref('smart_direct_print.view_smart_print_rule_form').id,
            'target': 'current',
            'context': {
                'default_name': f"{self.name} (Copy)",
                'default_printer_id': self.printer_id.id,
                'default_priority': self.priority,
                'default_user_id': self.user_id.id if self.user_id else False,
                'default_company_id': self.company_id.id if self.company_id else False,
                'default_workstation_name': self.workstation_name,
                'default_report_id': self.report_id.id if self.report_id else False,
                'default_model': self.model,
                'default_carrier_id': self.carrier_id.id if self.carrier_id else False,
                'default_document_type': self.document_type,
                'default_domain_filter': self.domain_filter,
                'default_copies': self.copies,
            }
        }
    