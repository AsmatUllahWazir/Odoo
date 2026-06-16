from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CarbonOffsetProject(models.Model):
    _name = 'carbon.offset.project'
    _description = 'Carbon Offset Project'
    _rec_name = 'project_name'
    _order = 'price_per_ton_usd'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    project_name = fields.Char(string='Project Name', required=True, tracking=True)
    project_code = fields.Char(string='Project Code', readonly=True, copy=False,
                               default=lambda self: self.env['ir.sequence'].next_by_code('carbon.offset.project.code') or 'NEW')
    project_type = fields.Selection([
        ('reforestation', '🌳 Reforestation & Afforestation'),
        ('solar', '☀️ Solar Energy'),
        ('wind', '💨 Wind Energy'),
        ('methane', '🏭 Methane Capture'),
        ('cookstoves', '🍳 Clean Cookstoves'),
        ('blue_carbon', '🌊 Blue Carbon (Mangroves)'),
    ], string='Project Type', required=True, tracking=True)

    # Location
    location = fields.Char(string='Location', required=True)
    country_id = fields.Many2one('res.country', string='Country')
    region = fields.Char(string='Region/State')

    # Certification
    certifying_body = fields.Selection([
        ('vcs', 'Verified Carbon Standard (VCS)'),
        ('gs', 'Gold Standard'),
        ('acr', 'American Carbon Registry'),
        ('car', 'Climate Action Reserve'),
    ], string='Certification Body', required=True, default='vcs', tracking=True)
    certificate_url = fields.Char(string='Certificate URL', help='Link to official project certification')
    verification_date = fields.Date(string='Latest Verification Date')
    is_verified = fields.Boolean(string='Verified', default=True, help='Project is properly verified')

    # Financial
    price_per_ton_usd = fields.Float(string='Price per Ton (USD)', required=True, default=15.0, tracking=True)
    available_credits_tons = fields.Float(string='Available Credits (tons)', required=True, default=10000.0, tracking=True)
    minimum_purchase_tons = fields.Float(string='Minimum Purchase (tons)', default=0.1)
    total_sold_tons = fields.Float(string='Total Sold (tons)', compute='_compute_sold', store=True)
    total_revenue_usd = fields.Float(string='Total Revenue (USD)', compute='_compute_sold', store=True)

    # Volume Discount Tiers
    discount_tier_1 = fields.Float(string='Discount for 10+ tons (%)', default=5.0)
    discount_tier_2 = fields.Float(string='Discount for 50+ tons (%)', default=10.0)
    discount_tier_3 = fields.Float(string='Discount for 100+ tons (%)', default=15.0)

    # Project Details
    start_date = fields.Date(string='Project Start Date')
    end_date = fields.Date(string='Project End Date')
    description = fields.Html(string='Description', help='Detailed description of the project')
    benefits = fields.Html(string='Environmental & Social Benefits')
    image_256 = fields.Image(string='Image', max_width=256, max_height=256)
    website_url = fields.Char(string='Project Website')
    is_featured = fields.Boolean(string='Featured Project', default=False)

    # Status
    is_active = fields.Boolean(string='Active', default=True, tracking=True)

    # Relationships
    purchase_ids = fields.One2many('carbon.offset.purchase', 'project_id', string='Purchases')

    @api.depends('purchase_ids.tons_offset')
    def _compute_sold(self):
        for project in self:
            project.total_sold_tons = sum(project.purchase_ids.mapped('tons_offset'))
            project.total_revenue_usd = sum(project.purchase_ids.mapped('total_cost_usd'))

    def get_discounted_price(self, tons):
        """Calculate discounted price based on volume"""
        self.ensure_one()
        if tons >= 100:
            discount = self.discount_tier_3
        elif tons >= 50:
            discount = self.discount_tier_2
        elif tons >= 10:
            discount = self.discount_tier_1
        else:
            discount = 0
        return self.price_per_ton_usd * (1 - discount / 100)

    def action_view_purchases(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Offset Purchases'),
            'res_model': 'carbon.offset.purchase',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
        }


class CarbonOffsetPurchase(models.Model):
    _name = 'carbon.offset.purchase'
    _description = 'Carbon Offset Purchase'
    _rec_name = 'display_name'
    _order = 'purchase_date DESC'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Display
    display_name = fields.Char(string='Reference', compute='_compute_display_name', store=True)

    # Relationships
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', related='sale_order_id.partner_id', string='Customer', store=True)
    company_id = fields.Many2one('res.company', related='sale_order_id.company_id', string='Company', store=True)
    project_id = fields.Many2one('carbon.offset.project', string='Carbon Offset Project', required=True,
                                 domain=[('is_active', '=', True)])

    # Amounts
    tons_offset = fields.Float(string='Tons CO2e Offset', required=True)
    offset_kg = fields.Float(string='Kilograms Offset', compute='_compute_kg', store=True)

    # Pricing with discount
    unit_price_usd = fields.Float(string='Unit Price (USD/ton)', compute='_compute_unit_price', store=True)
    discount_percentage = fields.Float(string='Discount %', compute='_compute_unit_price', store=True)
    total_cost_usd = fields.Float(string='Total Cost (USD)', compute='_compute_total_cost', store=True)
    total_cost_company_currency = fields.Monetary(string='Total Cost', compute='_compute_total_cost', store=True,
                                                   currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='sale_order_id.currency_id', store=True)

    # Dates
    purchase_date = fields.Date(string='Purchase Date', default=fields.Date.today, required=True, tracking=True)
    certificate_issue_date = fields.Date(string='Certificate Issue Date', readonly=True)

    # Certificate
    certificate_number = fields.Char(string='Certificate Number', copy=False, readonly=True)
    certificate_issued = fields.Boolean(string='Certificate Issued', default=False, tracking=True)
    certificate_qr = fields.Char(string='Certificate QR Data', compute='_compute_qr_data')

    # Communication
    notes = fields.Text(string='Notes')
    email_sent = fields.Boolean(string='Certificate Email Sent', default=False)

    @api.depends('sale_order_id', 'project_id', 'tons_offset')
    def _compute_display_name(self):
        for purchase in self:
            purchase.display_name = f"CO2-{purchase.id:06d} - {purchase.tons_offset:.2f}t - {purchase.partner_id.name}"

    @api.depends('tons_offset')
    def _compute_kg(self):
        for purchase in self:
            purchase.offset_kg = purchase.tons_offset * 1000

    @api.depends('tons_offset', 'project_id')
    def _compute_unit_price(self):
        for purchase in purchase:
            if purchase.project_id and purchase.tons_offset:
                discounted_price = purchase.project_id.get_discounted_price(purchase.tons_offset)
                original_price = purchase.project_id.price_per_ton_usd
                purchase.discount_percentage = ((original_price - discounted_price) / original_price * 100) if original_price > 0 else 0
                purchase.unit_price_usd = discounted_price
            else:
                purchase.unit_price_usd = 0
                purchase.discount_percentage = 0

    @api.depends('tons_offset', 'unit_price_usd', 'sale_order_id.currency_id', 'purchase_date')
    def _compute_total_cost(self):
        for purchase in self:
            usd_cost = purchase.tons_offset * purchase.unit_price_usd
            purchase.total_cost_usd = usd_cost
            if purchase.sale_order_id and purchase.sale_order_id.currency_id:
                purchase.total_cost_company_currency = purchase.sale_order_id.currency_id._convert(
                    usd_cost,
                    purchase.sale_order_id.company_id.currency_id,
                    purchase.sale_order_id.company_id,
                    purchase.purchase_date or fields.Date.today()
                )
            else:
                purchase.total_cost_company_currency = usd_cost

    @api.depends('certificate_number')
    def _compute_qr_data(self):
        for purchase in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            purchase.certificate_qr = f"{base_url}/carbon-offset/verify/{purchase.certificate_number}"

    @api.constrains('tons_offset')
    def _check_tons_offset(self):
        for purchase in self:
            if purchase.tons_offset <= 0:
                raise ValidationError(_("Tons offset must be greater than 0."))
            if purchase.project_id and purchase.tons_offset < purchase.project_id.minimum_purchase_tons:
                raise ValidationError(_("Minimum purchase is %.2f tons for this project.") % purchase.project_id.minimum_purchase_tons)
            if purchase.project_id and purchase.tons_offset > purchase.project_id.available_credits_tons + purchase.tons_offset:
                # Adding the current purchase to available check (for create)
                pass

    @api.model
    def create(self, vals):
        vals['certificate_number'] = self.env['ir.sequence'].next_by_code('carbon.offset.certificate') or '/'
        purchase = super().create(vals)

        # Reduce available credits from project
        purchase.project_id.available_credits_tons -= purchase.tons_offset

        # Update sale order
        purchase.sale_order_id.write({
            'carbon_offset_amount_kg': purchase.offset_kg,
            'offset_purchase_id': purchase.id,
        })

        # Send confirmation email
        if purchase.partner_id.email:
            template = self.env.ref('carbon_offset_pro.email_template_offset_confirmation', raise_if_not_found=False)
            if template:
                template.send_mail(purchase.id, force_send=True)

        return purchase

    def action_issue_certificate(self):
        self.ensure_one()
        if not self.certificate_issued:
            self.write({
                'certificate_issued': True,
                'certificate_issue_date': fields.Date.today(),
            })
        return self.env.ref('carbon_offset_pro.action_report_carbon_certificate').report_action(self)

    def action_send_certificate_email(self):
        self.ensure_one()
        if not self.partner_id.email:
            raise ValidationError(_("Customer has no email address configured."))

        template = self.env.ref('carbon_offset_pro.email_template_certificate', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.email_sent = True
        return True
