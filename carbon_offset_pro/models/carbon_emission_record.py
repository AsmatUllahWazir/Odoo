from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CarbonEmissionRecord(models.Model):
    _name = 'carbon.emission.record'
    _description = 'Carbon Emission Record'
    _rec_name = 'display_name'
    _order = 'record_date DESC, id DESC'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    display_name = fields.Char(string='Reference', compute='_compute_display_name', store=True)
    record_date = fields.Date(string='Record Date', default=fields.Date.today, required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # Source Traceability
    source_model = fields.Char(string='Source Model', help='e.g., sale.order, maintenance.request')
    source_id = fields.Integer(string='Source ID')
    source_ref = fields.Reference(string='Source Document', selection='_get_source_models')

    @api.model
    def _get_source_models(self):
        """Return available source models for the Reference field"""
        return [
            ('sale.order', 'Sale Order'),
            ('maintenance.request', 'Maintenance Request'),
            ('purchase.order', 'Purchase Order'),
            ('project.task', 'Project Task'),
            ('fleet.vehicle', 'Fleet Vehicle'),
        ]

    # Emission Details
    scope_id = fields.Many2one('carbon.scope', string='Scope', required=True, tracking=True)
    category_id = fields.Many2one('carbon.category', string='Category', required=True, tracking=True)
    factor_id = fields.Many2one('carbon.emission.factor', string='Emission Factor', required=True, tracking=True)

    # Activity Measurement
    activity_uom_id = fields.Many2one('uom.uom', string='Activity UoM', related='factor_id.uom_id', store=True)
    activity_quantity = fields.Float(string='Activity Quantity', required=True, default=1.0)
    calculated_co2e_kg = fields.Float(string='CO2e (kg)', compute='_compute_emission', store=True)
    calculated_co2e_tons = fields.Float(string='CO2e (tons)', compute='_compute_emission', store=True)

    # Record Metadata
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('offset', 'Offset'),
    ], string='Status', default='draft', tracking=True, copy=False, required=True)

    notes = fields.Text(string='Notes')
    submitted_by_id = fields.Many2one('res.users', string='Submitted By', readonly=True)
    submitted_date = fields.Datetime(string='Submitted Date', readonly=True)
    verified_by_id = fields.Many2one('res.users', string='Verified By', readonly=True)
    verified_date = fields.Datetime(string='Verified Date', readonly=True)

    # Relationships to Offsets
    offset_purchase_id = fields.Many2one('carbon.offset.purchase', string='Offset Purchase', readonly=True)
    is_offset = fields.Boolean(string='Is Offset', compute='_compute_offset_status', store=True)

    @api.depends('factor_id', 'activity_quantity')
    def _compute_emission(self):
        for record in self:
            if record.factor_id and record.activity_quantity:
                co2e = record.activity_quantity * record.factor_id.factor_value
                record.calculated_co2e_kg = co2e
                record.calculated_co2e_tons = co2e / 1000
            else:
                record.calculated_co2e_kg = 0.0
                record.calculated_co2e_tons = 0.0

    @api.depends('offset_purchase_id')
    def _compute_offset_status(self):
        for record in self:
            record.is_offset = bool(record.offset_purchase_id)

    @api.depends('source_model', 'source_id')
    def _compute_display_name(self):
        for record in self:
            model_name = dict(record._get_source_models()).get(record.source_model, 'Unknown')
            record.display_name = f"{record.record_date} - {model_name} #{record.source_id} - {record.calculated_co2e_kg:.2f} kg CO2e"

    @api.onchange('scope_id')
    def _onchange_scope(self):
        if self.scope_id:
            return {
                'domain': {
                    'category_id': [('scope_id', '=', self.scope_id.id)]
                }
            }

    @api.onchange('category_id')
    def _onchange_category(self):
        if self.category_id:
            return {
                'domain': {
                    'factor_id': [('category_id', '=', self.category_id.id), ('is_active', '=', True)]
                }
            }

    @api.constrains('activity_quantity')
    def _check_quantity(self):
        for record in self:
            if record.activity_quantity <= 0:
                raise ValidationError(_("Activity quantity must be greater than 0."))

    def action_submit(self):
        """Submit the emission record for verification"""
        for record in self:
            if record.state != 'draft':
                raise ValidationError(_("Only draft records can be submitted."))
            record.write({
                'state': 'submitted',
                'submitted_by_id': self.env.user.id,
                'submitted_date': fields.Datetime.now(),
            })

    def action_verify(self):
        """Verify the emission record"""
        for record in self:
            if record.state != 'submitted':
                raise ValidationError(_("Only submitted records can be verified."))
            record.write({
                'state': 'verified',
                'verified_by_id': self.env.user.id,
                'verified_date': fields.Datetime.now(),
            })

    def action_reject(self):
        """Reject the emission record"""
        for record in self:
            if record.state not in ['draft', 'submitted']:
                raise ValidationError(_("Only draft or submitted records can be rejected."))
            record.state = 'rejected'

    def action_mark_offset(self):
        """Mark the emission record as offset"""
        for record in self:
            if record.state != 'verified':
                raise ValidationError(_("Only verified records can be marked as offset."))
            record.state = 'offset'

    def action_create_offset_purchase(self):
        """Create an offset purchase from this emission record"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Carbon Offset'),
            'res_model': 'carbon.offset.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': False,
                'default_total_footprint_kg': self.calculated_co2e_kg,
                'default_total_footprint_tons': self.calculated_co2e_tons,
                'default_emission_record_id': self.id,
            }
        }

    @api.model
    def create_from_maintenance(self, maintenance_request):
        """Helper method to create an emission record from a maintenance request"""
        settings = self.env['carbon.config.settings'].get_settings()

        if not settings.get('maintenance_integration_enabled'):
            return False

        scope_id = settings.get('default_maintenance_scope_id')
        category_id = settings.get('default_maintenance_category_id')
        factor_id = settings.get('default_maintenance_factor_id')

        if not scope_id or not category_id or not factor_id:
            _logger.warning("Maintenance integration enabled but missing default values")
            return False

        record = self.create({
            'record_date': fields.Date.today(),
            'source_model': 'maintenance.request',
            'source_id': maintenance_request.id,
            'scope_id': scope_id,
            'category_id': category_id,
            'factor_id': factor_id,
            'activity_quantity': maintenance_request.duration or 1.0,
            'notes': f"Created from maintenance request {maintenance_request.name}",
        })

        if settings.get('auto_submit_maintenance'):
            record.action_submit()

        return record
    