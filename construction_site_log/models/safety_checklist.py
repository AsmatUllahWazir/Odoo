# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ConstructionSafetyChecklistTemplate(models.Model):
    """
    Reusable safety checklist templates.
    """
    _name = 'construction.safety.checklist.template'
    _description = 'Safety Checklist Template'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(
        string='Checklist Name',
        required=True,
        tracking=True,
        help='Name of the safety checklist template'
    )

    line_ids = fields.One2many(
        'construction.safety.checklist.template.line',
        'template_id',
        string='Checklist Items',
        copy=True
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive templates are hidden from selection'
    )

    description = fields.Text(
        string='Description',
        help='Detailed description of the checklist'
    )

    category = fields.Selection([
        ('general', 'General Safety'),
        ('electrical', 'Electrical Safety'),
        ('scaffolding', 'Scaffolding Safety'),
        ('excavation', 'Excavation Safety'),
        ('confined_space', 'Confined Space'),
        ('hot_work', 'Hot Work'),
        ('lifting', 'Lifting Operations'),
        ('ppe', 'Personal Protective Equipment'),
        ('fire', 'Fire Safety'),
        ('environmental', 'Environmental'),
        ('other', 'Other')
    ], string='Category',
        default='general')

    check_count = fields.Integer(
        compute='_compute_check_count',
        string='Number of Items'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.depends('line_ids')
    def _compute_check_count(self):
        """Compute number of checklist items."""
        for record in self:
            record.check_count = len(record.line_ids)

    def action_copy_template(self):
        """Create a copy of the template."""
        self.ensure_one()
        copy_vals = {
            'name': f"{self.name} (Copy)",
            'line_ids': [(0, 0, {
                'description': line.description,
                'sequence': line.sequence,
                'requires_photo': line.requires_photo,
                'allowed_response': line.allowed_response,
                'notes': line.notes,
            }) for line in self.line_ids],
        }
        return self.create(copy_vals)

    @api.constrains('name')
    def _check_name_unique(self):
        """Ensure template names are unique."""
        for record in self:
            existing = self.search([
                ('name', '=', record.name),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(_('A template with this name already exists.'))


class ConstructionSafetyChecklistTemplateLine(models.Model):
    """
    Lines for safety checklist templates.
    """
    _name = 'construction.safety.checklist.template.line'
    _description = 'Safety Checklist Template Line'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'construction.safety.checklist.template',
        string='Checklist Template',
        required=True,
        ondelete='cascade'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of items in the checklist'
    )

    description = fields.Text(
        string='Description',
        required=True,
        help='Description of the checklist item'
    )

    requires_photo = fields.Boolean(
        string='Requires Photo',
        help='Require photo evidence for this item'
    )

    allowed_response = fields.Selection([
        ('yes_no', 'Yes/No'),
        ('pass_fail', 'Pass/Fail'),
        ('text', 'Text Response'),
        ('yes_no_na', 'Yes/No/N/A')
    ], string='Allowed Response',
        default='yes_no',
        help='Type of response allowed for this item')

    required = fields.Boolean(
        string='Required',
        default=True,
        help='Must be completed for checklist to pass'
    )

    weight = fields.Float(
        string='Weight',
        default=1.0,
        help='Weight for scoring calculations'
    )

    notes = fields.Text(
        string='Notes',
        help='Additional notes for this item'
    )


class ConstructionSafetyChecklistExecution(models.Model):
    """
    Execution of safety checklists on site.
    """
    _name = 'construction.safety.checklist.execution'
    _description = 'Safety Checklist Execution'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Checklist Execution Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )

    template_id = fields.Many2one(
        'construction.safety.checklist.template',
        string='Checklist Template',
        required=True
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True
    )

    daily_log_id = fields.Many2one(
        'construction.site.daily.log',
        string='Daily Log',
        ondelete='set null'
    )

    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.today
    )

    executed_by_id = fields.Many2one(
        'hr.employee',
        string='Executed By',
        required=True,
        default=lambda self: self.env.user.employee_id
    )

    execution_line_ids = fields.One2many(
        'construction.safety.checklist.execution.line',
        'execution_id',
        string='Checklist Responses'
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Status',
        default='draft',
        tracking=True,
        required=True)

    result = fields.Selection([
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('partial', 'Partial Pass')
    ], compute='_compute_result',
        string='Result',
        store=True)

    pass_count = fields.Integer(
        compute='_compute_result_counts',
        string='Pass Count',
        store=True
    )

    fail_count = fields.Integer(
        compute='_compute_result_counts',
        string='Fail Count',
        store=True
    )

    na_count = fields.Integer(
        compute='_compute_result_counts',
        string='N/A Count',
        store=True
    )

    pass_rate = fields.Float(
        compute='_compute_result_counts',
        string='Pass Rate (%)',
        store=True
    )

    notes = fields.Text(
        string='Notes'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        """Override create to generate sequence number and create lines."""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'construction.safety.checklist.execution') or _('New')

        result = super().create(vals)

        # Automatically create execution lines from template
        if vals.get('template_id'):
            template = self.env['construction.safety.checklist.template'].browse(vals['template_id'])
            for line in template.line_ids:
                self.env['construction.safety.checklist.execution.line'].create({
                    'execution_id': result.id,
                    'template_line_id': line.id,
                    'sequence': line.sequence,
                })

        return result

    @api.depends('execution_line_ids.response_yes_no', 'execution_line_ids.response_pass_fail',
                 'execution_line_ids.response_text')
    def _compute_result(self):
        """Compute overall result of the checklist."""
        for record in self:
            if not record.execution_line_ids:
                record.result = False
                continue

            total_required = 0
            passed = 0
            failed = 0

            for line in record.execution_line_ids:
                if line.template_line_id.required:
                    total_required += 1

                    if line.allowed_response == 'yes_no':
                        if line.response_yes_no:
                            passed += 1
                        else:
                            failed += 1
                    elif line.allowed_response == 'pass_fail':
                        if line.response_pass_fail:
                            passed += 1
                        else:
                            failed += 1
                    elif line.allowed_response == 'text':
                        if line.response_text:
                            passed += 1
                        else:
                            failed += 1

            if total_required == 0:
                record.result = 'pass'
            elif failed == 0:
                record.result = 'pass'
            elif passed > 0:
                record.result = 'partial'
            else:
                record.result = 'fail'

    @api.depends('execution_line_ids')
    def _compute_result_counts(self):
        """Compute result counts for each line."""
        for record in self:
            pass_count = 0
            fail_count = 0
            na_count = 0

            for line in record.execution_line_ids:
                if line.allowed_response == 'yes_no':
                    if line.response_yes_no:
                        pass_count += 1
                    else:
                        fail_count += 1
                elif line.allowed_response == 'pass_fail':
                    if line.response_pass_fail:
                        pass_count += 1
                    else:
                        fail_count += 1
                elif line.allowed_response == 'text':
                    if line.response_text:
                        pass_count += 1
                    else:
                        fail_count += 1
                elif line.allowed_response == 'yes_no_na':
                    if line.response_yes_no:
                        pass_count += 1
                    elif not line.response_yes_no and not line.is_na:
                        fail_count += 1
                    else:
                        na_count += 1

            record.pass_count = pass_count
            record.fail_count = fail_count
            record.na_count = na_count

            total = pass_count + fail_count
            record.pass_rate = (pass_count / total * 100) if total > 0 else 0.0

    def action_start(self):
        """Start the checklist execution."""
        self.ensure_one()

        if self.status != 'draft':
            raise ValidationError(_('Only draft checklists can be started.'))

        self.write({'status': 'in_progress'})

        self.message_post(
            body=_("""
                <b>Checklist Started</b><br/>
                Checklist: %s<br/>
                Started by: %s
            """) % (
                self.name,
                self.env.user.name
            ),
            subject=_('Checklist Started')
        )

    def action_complete(self):
        """Complete the checklist execution."""
        self.ensure_one()

        if self.status == 'completed':
            raise ValidationError(_('This checklist is already completed.'))

        # Validate all required lines are completed
        for line in self.execution_line_ids:
            if line.template_line_id.required:
                if line.allowed_response == 'yes_no' and not line.response_yes_no:
                    raise ValidationError(
                        _('Please complete required item: %s') % line.template_line_id.description
                    )
                elif line.allowed_response == 'pass_fail' and not line.response_pass_fail:
                    raise ValidationError(
                        _('Please complete required item: %s') % line.template_line_id.description
                    )
                elif line.allowed_response == 'text' and not line.response_text:
                    raise ValidationError(
                        _('Please complete required item: %s') % line.template_line_id.description
                    )

        self.write({'status': 'completed'})

        # Generate result message
        result_msg = {
            'pass': '✅ Passed',
            'fail': '❌ Failed',
            'partial': '⚠️ Partial Pass'
        }.get(self.result, 'Unknown')

        self.message_post(
            body=_("""
                <b>Checklist Completed</b><br/>
                Checklist: %s<br/>
                Result: %s<br/>
                Pass Rate: %.1f%%<br/>
                Completed by: %s
            """) % (
                self.name,
                result_msg,
                self.pass_rate,
                self.env.user.name
            ),
            subject=_('Checklist Completed')
        )

    def action_view_report(self):
        """View the checklist report."""
        self.ensure_one()

        return self.env.ref('construction_site_log.action_report_construction_checklist').report_action(self)

    @api.constrains('template_id')
    def _check_template_active(self):
        """Ensure template is active."""
        for record in self:
            if not record.template_id.active:
                raise ValidationError(_('Cannot use an inactive template.'))


class ConstructionSafetyChecklistExecutionLine(models.Model):
    """
    Lines for safety checklist execution.
    """
    _name = 'construction.safety.checklist.execution.line'
    _description = 'Safety Checklist Execution Line'
    _order = 'sequence, id'

    execution_id = fields.Many2one(
        'construction.safety.checklist.execution',
        string='Checklist Execution',
        required=True,
        ondelete='cascade'
    )

    template_line_id = fields.Many2one(
        'construction.safety.checklist.template.line',
        string='Checklist Item',
        required=True,
        ondelete='restrict'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

    description = fields.Text(
        string='Description',
        related='template_line_id.description',
        readonly=True
    )

    allowed_response = fields.Selection(
        string='Allowed Response',
        related='template_line_id.allowed_response',
        readonly=True
    )

    requires_photo = fields.Boolean(
        string='Requires Photo',
        related='template_line_id.requires_photo',
        readonly=True
    )

    required = fields.Boolean(
        string='Required',
        related='template_line_id.required',
        readonly=True
    )

    response_yes_no = fields.Boolean(
        string='Yes',
        help='Select if the item is compliant'
    )

    response_pass_fail = fields.Boolean(
        string='Pass',
        help='Select if the item passes'
    )

    response_text = fields.Text(
        string='Response',
        help='Text response for the item'
    )

    is_na = fields.Boolean(
        string='N/A',
        help='Not Applicable'
    )

    photo_attachment_ids = fields.Many2many(
        'ir.attachment',
        'checklist_line_photo_rel',
        'line_id',
        'attachment_id',
        string='Photos'
    )

    notes = fields.Text(
        string='Notes'
    )

    @api.onchange('template_line_id')
    def _onchange_template_line_id(self):
        """Set sequence from template line."""
        if self.template_line_id:
            self.sequence = self.template_line_id.sequence

    @api.constrains('response_yes_no', 'response_pass_fail', 'response_text')
    def _check_response(self):
        """Validate response based on allowed response type."""
        for record in self:
            if record.allowed_response == 'yes_no':
                pass
            elif record.allowed_response == 'pass_fail':
                pass
            elif record.allowed_response == 'text':
                if not record.response_text and record.required:
                    raise ValidationError(_('Text response is required for this item.'))
