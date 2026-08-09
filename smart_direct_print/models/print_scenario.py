# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SmartPrintScenario(models.Model):
    """
    Print Scenario Model

    Represents an automatic printing configuration.
    A scenario defines when and what should be printed automatically.
    """
    _name = 'smart.print.scenario'
    _description = 'Smart Print Scenario'
    _order = 'priority desc, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Scenario Name',
        required=True,
        tracking=True,
        help='A descriptive name for this scenario'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Enable or disable this scenario'
    )
    priority = fields.Integer(
        string='Priority',
        default=10,
        tracking=True,
        help='Higher priority means the scenario is evaluated first'
    )

    # Action & Report
    action_id = fields.Many2one(
        'smart.print.scenario.action',
        string='Action',
        required=True,
        tracking=True,
        help='The action that triggers this scenario'
    )
    report_id = fields.Many2one(
        'ir.actions.report',
        string='Report',
        required=True,
        tracking=True,
        help='Report to print when this scenario is triggered'
    )

    # Printer & Printing
    printer_rule_id = fields.Many2one(
        'smart.print.rule',
        string='Printer Rule',
        help='Rule to select printer for this scenario. If not set, the default resolution logic is used.'
    )
    number_of_copies = fields.Integer(
        string='Copies',
        default=1,
        min=1,
        max=999,
        tracking=True,
        help='Number of copies to print'
    )
    document_format = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('esc_pos', 'ESC/POS'),
        ('raw', 'RAW'),
    ], string='Document Format', default='pdf', tracking=True)

    # Conditions
    condition_filter = fields.Text(
        string='Condition Filter',
        help='Domain filter to determine when to apply this scenario\n'
             'Example: [(\'state\', \'in\', [\'confirmed\', \'done\'])]'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Company this scenario belongs to'
    )

    # Additional
    description = fields.Text(
        string='Description',
        help='Additional notes about this scenario'
    )

    _sql_constraints = [
        ('unique_name_company', 'unique(name, company_id)',
         'Scenario name must be unique per company!')
    ]

    @api.constrains('condition_filter')
    def _check_condition_filter(self):
        """Validate the condition filter expression."""
        for scenario in self:
            if scenario.condition_filter:
                try:
                    eval(scenario.condition_filter)
                except Exception as e:
                    raise ValidationError(_(
                        'Invalid condition filter expression: %s'
                    ) % str(e))

    def execute_scenario(self, record, **kwargs):
        """
        Execute the print scenario for a given record.

        Args:
            record (Model): Record to print
            **kwargs: Additional context

        Returns:
            smart.print.job: The created print job or False
        """
        self.ensure_one()

        if not self.active:
            return False

        # Check if record matches the condition filter
        if self.condition_filter:
            try:
                domain = eval(self.condition_filter)
                if not record.filtered_domain(domain):
                    return False
            except Exception as e:
                _logger.error(f"Condition filter evaluation failed: {e}")
                return False

        # Get printer
        printer = self._get_printer(record, **kwargs)
        if not printer:
            _logger.warning(f"No printer found for scenario {self.name}")
            return False

        # Get report
        report = self.report_id
        if not report:
            _logger.warning(f"No report configured for scenario {self.name}")
            return False

        # Create and send print job
        return self._create_print_job(record, printer, report, **kwargs)

    def _get_printer(self, record, **kwargs):
        """
        Get the appropriate printer for this scenario.

        Args:
            record (Model): Record being printed
            **kwargs: Additional context

        Returns:
            smart.printer: The selected printer or None
        """
        if self.printer_rule_id:
            return self.printer_rule_id.printer_id

        # Use the central printer resolution engine
        resolver = self.env['smart.printer.resolver']
        return resolver.get_printer_for_document(
            model=record._name,
            record=record,
            report=self.report_id,
            user=kwargs.get('user', self.env.user),
            company=kwargs.get('company', self.env.company),
            **kwargs
        )

    def _create_print_job(self, record, printer, report, **kwargs):
        """
        Create and send the print job.

        Args:
            record (Model): Record being printed
            printer (smart.printer): Selected printer
            report (ir.actions.report): Report to print
            **kwargs: Additional context

        Returns:
            smart.print.job: The created print job
        """
        PrintJob = self.env['smart.print.job']

        job_vals = {
            'printer_id': printer.id,
            'user_id': kwargs.get('user', self.env.user).id,
            'model': record._name,
            'res_id': record.id,
            'report_id': report.id,
            'number_of_copies': self.number_of_copies,
            'document_format': kwargs.get('format', self.document_format),
            'priority': self.priority,
        }

        job = PrintJob.create(job_vals)

        # Validate and send immediately
        job.action_validate()
        job.action_queue()

        _logger.info(f"Scenario {self.name} created job {job.name} for {record._name}:{record.id}")

        return job

    @api.model
    def trigger_scenarios(self, action_code, records, **kwargs):
        """
        Trigger scenarios for a given action code and records.

        Args:
            action_code (str): Action code to trigger
            records (Model): Records to process
            **kwargs: Additional context

        Returns:
            list: List of created print jobs
        """
        if not records:
            return []

        # Find matching actions
        scenario_actions = self.env['smart.print.scenario.action'].search([
            ('code', '=', action_code),
            ('active', '=', True)
        ])

        if not scenario_actions:
            return []

        triggered_jobs = []

        for action in scenario_actions:
            # Find scenarios for this action
            scenarios = self.search([
                ('action_id', '=', action.id),
                ('active', '=', True),
                '|',
                ('company_id', '=', self.env.company.id),
                ('company_id', '=', False)
            ])

            for record in records:
                for scenario in scenarios:
                    try:
                        job = scenario.execute_scenario(record, **kwargs)
                        if job:
                            triggered_jobs.append(job)
                    except Exception as e:
                        _logger.error(
                            f"Failed to execute scenario {scenario.name} "
                            f"for {record._name}:{record.id}: {e}"
                        )

        return triggered_jobs

    def action_preview(self):
        """
        Preview the report for this scenario.

        Returns:
            dict: Action to preview the report
        """
        self.ensure_one()

        if not self.report_id:
            raise UserError(_('No report configured for this scenario'))

        # Get a sample record
        model = self.env.get(self.report_id.model)
        if not model:
            raise UserError(_('Report model not found'))

        sample = model.search([], limit=1)
        if not sample:
            raise UserError(_('No records found to preview'))

        return self.report_id.action_print(sample.ids)
    