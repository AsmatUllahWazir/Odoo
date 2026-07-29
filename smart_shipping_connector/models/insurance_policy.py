from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ShippingInsurancePolicy(models.Model):
    """Shipping Insurance Policy"""
    _name = 'shipping.insurance.policy'
    _description = 'Shipping Insurance Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Policy Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipment',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    insurance_provider = fields.Char(
        string='Insurance Provider',
        required=True,
        tracking=True,
    )
    policy_number = fields.Char(string='Policy Number', tracking=True)

    # Coverage
    coverage_amount = fields.Monetary(
        string='Coverage Amount',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Amount insured'
    )
    premium = fields.Monetary(
        string='Premium',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Insurance premium paid'
    )
    deductible = fields.Monetary(
        string='Deductible',
        currency_field='currency_id',
        help='Deductible amount'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # Coverage Details
    coverage_type = fields.Selection([
        ('all_risk', 'All Risk'),
        ('named_perils', 'Named Perils'),
        ('limited', 'Limited'),
        ('total_loss', 'Total Loss Only'),
    ], string='Coverage Type', default='all_risk')

    perils_covered = fields.Text(string='Perils Covered')
    exclusions = fields.Text(string='Exclusions')

    # Dates
    effective_date = fields.Datetime(
        string='Effective Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
    )
    expiry_date = fields.Datetime(
        string='Expiry Date',
        required=True,
        tracking=True,
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('claimed', 'Claimed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Claims
    claim_count = fields.Integer(
        string='Number of Claims',
        compute='_compute_claim_count',
        store=True,
    )
    claim_ids = fields.One2many(
        'shipping.insurance.claim',
        'policy_id',
        string='Claims',
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('unique_policy', 'unique(policy_number)', 'Policy number must be unique!'),
        ('check_coverage_positive', 'CHECK(coverage_amount >= 0)', 'Coverage amount cannot be negative.'),
    ]

    @api.depends('claim_ids')
    def _compute_claim_count(self):
        for policy in self:
            policy.claim_count = len(policy.claim_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.insurance.policy') or _('New')
        return super(ShippingInsurancePolicy, self).create(vals)

    def action_activate(self):
        """Activate insurance policy"""
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'active'
            self.message_post(body=_('Insurance policy activated.'))

    def action_expire(self):
        """Expire insurance policy"""
        self.ensure_one()
        if self.state == 'active':
            self.state = 'expired'
            self.message_post(body=_('Insurance policy expired.'))

    def action_cancel(self):
        """Cancel insurance policy"""
        self.ensure_one()
        if self.state != 'claimed':
            self.state = 'cancelled'
            self.message_post(body=_('Insurance policy cancelled.'))

    def action_view_claims(self):
        """View claims for this policy"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Insurance Claims'),
            'res_model': 'shipping.insurance.claim',
            'view_mode': 'tree,form',
            'domain': [('policy_id', '=', self.id)],
        }


class ShippingInsuranceClaim(models.Model):
    """Insurance Claim"""
    _name = 'shipping.insurance.claim'
    _description = 'Insurance Claim'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Claim Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    policy_id = fields.Many2one(
        'shipping.insurance.policy',
        string='Insurance Policy',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipment',
        related='policy_id.shipment_id',
        store=True,
    )

    claim_date = fields.Datetime(
        string='Claim Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    incident_date = fields.Datetime(
        string='Incident Date',
        required=True,
        tracking=True,
    )

    claim_amount = fields.Monetary(
        string='Claim Amount',
        currency_field='currency_id',
        required=True,
        tracking=True,
    )
    approved_amount = fields.Monetary(
        string='Approved Amount',
        currency_field='currency_id',
        tracking=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    claim_type = fields.Selection([
        ('damage', 'Damage'),
        ('loss', 'Loss'),
        ('theft', 'Theft'),
        ('delay', 'Delay'),
        ('other', 'Other'),
    ], string='Claim Type', required=True, tracking=True)

    description = fields.Text(string='Description', required=True)
    resolution = fields.Text(string='Resolution')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('investigating', 'Investigating'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)

    supporting_documents = fields.Binary(string='Supporting Documents', attachment=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.insurance.claim') or _('New')
        return super(ShippingInsuranceClaim, self).create(vals)

    def action_submit(self):
        """Submit claim"""
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'submitted'
            self.message_post(body=_('Insurance claim submitted.'))

    def action_approve(self):
        """Approve claim"""
        self.ensure_one()
        if self.state in ['submitted', 'investigating']:
            self.state = 'approved'
            self.approved_amount = self.claim_amount
            self.message_post(body=_('Insurance claim approved.'))

    def action_reject(self):
        """Reject claim"""
        self.ensure_one()
        if self.state in ['submitted', 'investigating']:
            self.state = 'rejected'
            self.message_post(body=_('Insurance claim rejected.'))

    def action_pay(self):
        """Mark as paid"""
        self.ensure_one()
        if self.state == 'approved':
            self.state = 'paid'
            self.message_post(body=_('Insurance claim paid.'))

    @api.model
    def action_auto_expire(self):
        """Auto-expire insurance policies"""
        policies = self.search([
            ('state', '=', 'active'),
            ('expiry_date', '<', fields.Datetime.now())
        ])
        for policy in policies:
            policy.action_expire()
        _logger.info(f"Auto-expired {len(policies)} insurance policies")
        return True