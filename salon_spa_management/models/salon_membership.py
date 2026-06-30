# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta
import base64


class SalonMembership(models.Model):
    _name = 'salon.membership'
    _description = 'Salon Membership'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Membership Name', required=True, translate=True)
    code = fields.Char(string='Membership Code', required=True)

    type = fields.Selection([
        ('prepaid', 'Prepaid'),
        ('subscription', 'Subscription'),
        ('tier', 'Tier Based'),
    ], string='Membership Type', required=True, default='tier')

    tier_level = fields.Integer(string='Tier Level', help='Higher number = higher tier')

    discount_percentage = fields.Float(string='Discount %', default=0)
    service_category_ids = fields.Many2many('salon.service.category',
                                            string='Discounted Service Categories')

    duration = fields.Integer(string='Duration (Days)', help='0 for lifetime')

    price = fields.Monetary(string='Membership Price', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    benefits = fields.Text(string='Benefits Description', translate=True)

    is_active = fields.Boolean(string='Active', default=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.constrains('code')
    def _check_code(self):
        for membership in self:
            if self.search_count([('code', '=', membership.code), ('id', '!=', membership.id)]) > 0:
                raise ValidationError(_('Membership code must be unique.'))

    @api.constrains('discount_percentage')
    def _check_discount(self):
        for membership in self:
            if membership.discount_percentage < 0 or membership.discount_percentage > 100:
                raise ValidationError(_('Discount percentage must be between 0 and 100.'))


class SalonMembershipCard(models.Model):
    _name = 'salon.membership.card'
    _description = 'Membership Card'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ]

    name = fields.Char(string='Card Number', required=True, copy=False, default='/')

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    membership_id = fields.Many2one('salon.membership', string='Membership Plan', required=True)

    start_date = fields.Date(string='Start Date', default=fields.Date.today, required=True)
    expiry_date = fields.Date(string='Expiry Date', compute='_compute_expiry_date', store=True)

    state = fields.Selection(STATES, string='Status', default='active', tracking=True)

    remaining_balance = fields.Monetary(string='Remaining Balance', default=0.0)
    total_spent = fields.Monetary(string='Total Spent', compute='_compute_total_spent')

    discount_percentage = fields.Float(string='Discount %', compute='_compute_discount')

    barcode = fields.Char(string='Barcode')
    barcode_image = fields.Binary(string='Barcode Image', compute='_compute_barcode_image')

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='company_id.currency_id')

    @api.depends('start_date', 'membership_id.duration')
    def _compute_expiry_date(self):
        for card in self:
            if card.membership_id and card.membership_id.duration > 0:
                card.expiry_date = card.start_date + timedelta(days=card.membership_id.duration)
            else:
                card.expiry_date = False

    @api.depends('membership_id.discount_percentage')
    def _compute_discount(self):
        for card in self:
            card.discount_percentage = card.membership_id.discount_percentage or 0

    @api.depends('partner_id.order_ids')
    def _compute_total_spent(self):
        for card in self:
            orders = self.env['salon.order'].search([
                ('partner_id', '=', card.partner_id.id),
                ('state', '=', 'done')
            ])
            card.total_spent = sum(orders.mapped('total_amount'))

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('salon.membership.card') or '/'
        return super(SalonMembershipCard, self).create(vals)

    def action_activate(self):
        for record in self:
            record.state = 'active'

    def action_suspend(self):
        for record in self:
            record.state = 'suspended'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def _compute_barcode_image(self):
        """Generate barcode image for membership card"""
        for card in self:
            if card.barcode:
                # Generate barcode using Odoo's barcode generation
                try:
                    barcode_generator = self.env['barcode.generate']
                    barcode_data = barcode_generator.generate(card.barcode, 'code128')
                    card.barcode_image = base64.b64encode(barcode_data)
                except:
                    card.barcode_image = False
                    