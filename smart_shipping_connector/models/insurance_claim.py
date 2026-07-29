from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


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
        tracking=True,
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
    paid_amount = fields.Monetary(
        string='Paid Amount',
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
        ('non_delivery', 'Non-Delivery'),
        ('shortage', 'Shortage'),
        ('other', 'Other'),
    ], string='Claim Type', required=True, tracking=True)

    claim_subtype = fields.Selection([
        ('partial', 'Partial'),
        ('total', 'Total'),
        ('replacement', 'Replacement'),
    ], string='Claim Subtype', default='partial')

    description = fields.Text(string='Description', required=True)
    resolution = fields.Text(string='Resolution')

    # Supporting Documents
    document_ids = fields.One2many(
        'shipping.claim.document',
        'claim_id',
        string='Supporting Documents',
        help='Supporting documents for the claim'
    )

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('investigating', 'Investigating'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)

    # Investigation
    investigator_id = fields.Many2one(
        'res.users',
        string='Investigator',
        tracking=True,
    )
    investigation_notes = fields.Text(string='Investigation Notes')
    investigation_date = fields.Datetime(string='Investigation Date')

    # Payment
    payment_date = fields.Datetime(string='Payment Date')
    payment_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('other', 'Other'),
    ], string='Payment Method')
    payment_reference = fields.Char(string='Payment Reference')

    # Rejection
    rejection_reason = fields.Text(string='Rejection Reason')
    rejection_date = fields.Datetime(string='Rejection Date')

    # Notes
    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('check_claim_positive', 'CHECK(claim_amount >= 0)',
         'Claim amount cannot be negative.'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.insurance.claim') or _('New')
        return super(ShippingInsuranceClaim, self).create(vals)

    @api.constrains('claim_amount')
    def _check_claim_amount(self):
        for claim in self:
            if claim.claim_amount <= 0:
                raise ValidationError(_('Claim amount must be greater than 0.'))

    @api.constrains('approved_amount', 'claim_amount')
    def _check_approved_amount(self):
        for claim in self:
            if claim.approved_amount and claim.approved_amount > claim.claim_amount:
                raise ValidationError(_('Approved amount cannot exceed claim amount.'))

    def action_submit(self):
        """Submit claim"""
        self.ensure_one()
        if self.status == 'draft':
            self.status = 'submitted'
            self.message_post(body=_('Insurance claim submitted.'))

    def action_investigate(self):
        """Start investigation"""
        self.ensure_one()
        if self.status == 'submitted':
            self.status = 'investigating'
            self.investigator_id = self.env.user
            self.investigation_date = fields.Datetime.now()
            self.message_post(body=_('Investigation started.'))

    def action_approve(self):
        """Approve claim"""
        self.ensure_one()
        if self.status in ['submitted', 'investigating']:
            self.status = 'approved'
            self.approved_amount = self.approved_amount or self.claim_amount
            self.message_post(
                body=_('Insurance claim approved for %s') % self.approved_amount
            )

    def action_reject(self):
        """Reject claim"""
        self.ensure_one()
        if self.status in ['submitted', 'investigating']:
            self.status = 'rejected'
            self.rejection_date = fields.Datetime.now()
            self.message_post(body=_('Insurance claim rejected.'))

    def action_pay(self):
        """Pay claim"""
        self.ensure_one()
        if self.status == 'approved':
            self.status = 'paid'
            self.payment_date = fields.Datetime.now()
            self.paid_amount = self.approved_amount or self.claim_amount
            self.message_post(
                body=_('Insurance claim paid: %s') % self.paid_amount
            )

    def action_close(self):
        """Close claim"""
        self.ensure_one()
        if self.status in ['paid', 'approved']:
            self.status = 'closed'
            self.message_post(body=_('Claim closed.'))

    def action_view_policy(self):
        """View insurance policy"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Insurance Policy'),
            'res_model': 'shipping.insurance.policy',
            'res_id': self.policy_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_shipment(self):
        """View shipment"""
        self.ensure_one()
        if self.shipment_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Shipment'),
                'res_model': 'shipping.shipment',
                'res_id': self.shipment_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}


class ShippingClaimDocument(models.Model):
    """Supporting Document for Insurance Claim"""
    _name = 'shipping.claim.document'
    _description = 'Claim Supporting Document'
    _order = 'claim_id, sequence'
    _rec_name = 'name'

    claim_id = fields.Many2one(
        'shipping.insurance.claim',
        string='Claim',
        required=True,
        ondelete='cascade',
    )

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Document Name', required=True)

    document_type = fields.Selection([
        ('photo', 'Photo'),
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('packing_slip', 'Packing Slip'),
        ('delivery_confirmation', 'Delivery Confirmation'),
        ('damage_report', 'Damage Report'),
        ('police_report', 'Police Report'),
        ('other', 'Other'),
    ], string='Document Type', default='other')

    document = fields.Binary(
        string='Document',
        attachment=True,
        required=True,
    )
    filename = fields.Char(string='Filename')

    description = fields.Text(string='Description')
    uploaded_date = fields.Datetime(
        string='Uploaded Date',
        default=fields.Datetime.now,
    )
    uploaded_by = fields.Many2one(
        'res.users',
        string='Uploaded By',
        default=lambda self: self.env.user,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
