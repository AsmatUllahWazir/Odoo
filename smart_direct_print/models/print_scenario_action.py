# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class SmartPrintScenarioAction(models.Model):
    """
    Print Scenario Action Model

    Defines technical triggers for automatic printing scenarios.
    Actions are the triggers that start automatic printing scenarios.
    Each action has a unique code that can be triggered from code.
    """
    _name = 'smart.print.scenario.action'
    _description = 'Smart Print Scenario Action'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Action Name',
        required=True,
        tracking=True,
        help='A descriptive name for this action'
    )
    code = fields.Char(
        string='Action Code',
        required=True,
        tracking=True,
        help='Unique code to identify this action for triggering\n'
             'Example: sale_order_confirmed, stock_picking_validated'
    )
    description = fields.Text(
        string='Description',
        help='Detailed description of when this action should be triggered'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Enable or disable this action'
    )

    # Model Information
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        help='The model this action applies to'
    )
    model_name = fields.Char(
        string='Model Name',
        related='model_id.model',
        store=True,
        readonly=True,
        help='Technical name of the model'
    )
    report_model_id = fields.Many2one(
        'ir.model',
        string='Report Model',
        help='The model used for reports (if different from the main model)'
    )
    report_model_name = fields.Char(
        string='Report Model Name',
        related='report_model_id.model',
        store=True,
        readonly=True,
        help='Technical name of the report model'
    )

    # Integration
    method_name = fields.Char(
        string='Method Name',
        help='Name of the method to call for custom triggers\n'
             'Example: _smart_print_scenario_sale_order_confirmed'
    )

    # Statistics
    scenario_count = fields.Integer(
        string='Number of Scenarios',
        compute='_compute_scenario_count',
        store=True,
        help='Number of scenarios using this action'
    )
    last_triggered = fields.Datetime(
        string='Last Triggered',
        readonly=True,
        help='When this action was last triggered'
    )
    trigger_count = fields.Integer(
        string='Trigger Count',
        default=0,
        readonly=True,
        help='Number of times this action has been triggered'
    )

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Action code must be unique!')
    ]

    @api.constrains('code')
    def _check_code_format(self):
        """Validate action code format."""
        for action in self:
            if action.code:
                # Only allow letters, numbers, and underscores
                if not all(c.isalnum() or c == '_' for c in action.code):
                    raise ValidationError(_(
                        'Action code must contain only letters, numbers, and underscores'
                    ))
                # Must start with a letter or underscore
                if not (action.code[0].isalpha() or action.code[0] == '_'):
                    raise ValidationError(_(
                        'Action code must start with a letter or underscore'
                    ))
                # Must not be a Python keyword
                import keyword
                if keyword.iskeyword(action.code):
                    raise ValidationError(_(
                        'Action code cannot be a Python keyword: %s'
                    ) % action.code)

    @api.constrains('model_id', 'report_model_id')
    def _check_model_consistency(self):
        """Check model consistency."""
        for action in self:
            if action.model_id and action.report_model_id:
                # Both models should be related or the same
                model_obj = self.env.get(action.model_id.model)
                report_obj = self.env.get(action.report_model_id.model)
                if model_obj and report_obj:
                    # Check if they are the same or related
                    if model_obj._name != report_obj._name:
                        # They might be related through a field
                        # This is just a warning, not an error
                        _logger.info(
                            f"Action {action.name}: Model {action.model_id.model} "
                            f"and report model {action.report_model_id.model} are different"
                        )

    @api.depends('code')
    def _compute_scenario_count(self):
        """Compute the number of scenarios using this action."""
        for action in self:
            action.scenario_count = self.env['smart.print.scenario'].search_count([
                ('action_id', '=', action.id),
                ('active', '=', True)
            ])

    @api.model
    def trigger_by_code(self, action_code, records, **kwargs):
        """
        Trigger actions by code.

        This is the main entry point for triggering print scenarios from code.

        Args:
            action_code (str): Action code to trigger
            records (Model): Records to process
            **kwargs: Additional context including:
                - user: res.users record (default: current user)
                - company: res.company record (default: current company)
                - format: document format (default: pdf)
                - printer: specific printer to use
                - copies: number of copies (default: 1)
                - force: bool to force printing even if disabled (default: False)

        Returns:
            list: List of created print jobs
        """
        if not records:
            _logger.warning(f"trigger_by_code called with empty records for action {action_code}")
            return []

        # Find matching actions
        actions = self.search([
            ('code', '=', action_code),
            ('active', '=', True)
        ])

        if not actions:
            _logger.info(f"No active actions found for code: {action_code}")
            return []

        # Get user and company from kwargs or context
        user = kwargs.get('user', kwargs.get('env', {}).get('user', None))
        if not user:
            user = self.env.user

        company = kwargs.get('company', user.company_id)

        # Check if auto-print is enabled for the user
        if not kwargs.get('force', False):
            if not user.auto_print_enabled:
                _logger.info(
                    f"Auto-print disabled for user {user.name}, "
                    f"skipping action {action_code}"
                )
                return []

        # Trigger all matching actions
        triggered_jobs = []
        scenario_model = self.env['smart.print.scenario']

        for action in actions:
            try:
                # Check if action matches the model
                if action.model_id:
                    # Filter records by model
                    filtered_records = records.filtered(
                        lambda r: r._name == action.model_id.model
                    )
                    if not filtered_records:
                        continue
                else:
                    filtered_records = records

                # Trigger scenarios for this action
                jobs = scenario_model.trigger_scenarios(
                    action.code,
                    filtered_records,
                    **kwargs
                )
                triggered_jobs.extend(jobs)

                # Update action statistics
                action.write({
                    'last_triggered': fields.Datetime.now(),
                    'trigger_count': action.trigger_count + 1
                })

            except Exception as e:
                _logger.error(
                    f"Failed to trigger action {action.code} for {records._name}: {e}"
                )
                # Continue with other actions

        if triggered_jobs:
            _logger.info(
                f"Action {action_code} triggered {len(triggered_jobs)} "
                f"print jobs for {len(records)} records"
            )

        return triggered_jobs

    def action_trigger_manually(self):
        """
        Manually trigger this action for testing.

        This method is used for testing purposes to verify
        that the action works correctly.

        Returns:
            dict: Action result with notification
        """
        self.ensure_one()

        if not self.model_id:
            raise UserError(_('No model configured for this action'))

        # Get records to test with
        model = self.env.get(self.model_id.model)
        if not model:
            raise UserError(_('Model %s not found') % self.model_id.model)

        # Get up to 10 records for testing
        records = model.search([], limit=10)
        if not records:
            raise UserError(_('No records found to test with'))

        try:
            jobs = self.trigger_by_code(self.code, records)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Action Triggered'),
                    'message': _(
                        'Triggered %(count)s print jobs for %(records)s records'
                    ) % {
                                   'count': len(jobs),
                                   'records': len(records)
                               },
                    'type': 'success' if jobs else 'info',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Failed to trigger action: %s') % str(e))

    def action_view_scenarios(self):
        """
        View scenarios using this action.

        Returns:
            dict: Action to view related scenarios
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Scenarios for %s') % self.name,
            'res_model': 'smart.print.scenario',
            'view_mode': 'tree,form',
            'domain': [('action_id', '=', self.id)],
            'context': {'default_action_id': self.id},
        }

    def action_duplicate(self):
        """
        Duplicate this action.

        Returns:
            dict: Action to create a new action with the same values
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.print.scenario.action',
            'view_mode': 'form',
            'view_id': self.env.ref('smart_direct_print.view_smart_print_scenario_action_form').id,
            'target': 'current',
            'context': {
                'default_name': f"{self.name} (Copy)",
                'default_code': f"{self.code}_copy",
                'default_description': self.description,
                'default_model_id': self.model_id.id if self.model_id else False,
                'default_report_model_id': self.report_model_id.id if self.report_model_id else False,
                'default_method_name': self.method_name,
            }
        }

    def action_toggle_active(self):
        """Toggle the active state of the action."""
        self.ensure_one()
        self.write({'active': not self.active})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Action Updated'),
                'message': _('Action %s is now %s') % (
                    self.name,
                    _('Active') if self.active else _('Inactive')
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def get_actions_for_model(self, model_name):
        """
        Get all actions for a given model.

        Args:
            model_name (str): Technical name of the model

        Returns:
            smart.print.scenario.action: Actions for the model
        """
        return self.search([
            ('active', '=', True),
            '|',
            ('model_id.model', '=', model_name),
            ('model_id', '=', False)
        ])

    @api.model
    def get_trigger_methods(self):
        """
        Get all trigger methods defined in the system.

        Returns:
            list: List of method names
        """
        methods = []
        for action in self.search([('method_name', '!=', False)]):
            methods.append({
                'id': action.id,
                'name': action.name,
                'code': action.code,
                'method': action.method_name,
                'model': action.model_id.model if action.model_id else '',
            })
        return methods
