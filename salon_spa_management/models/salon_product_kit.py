# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SalonProductKit(models.Model):
    _name = 'salon.product.kit'
    _description = 'Salon Product Kit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Kit Name', required=True)
    service_id = fields.Many2one('salon.service', string='Service', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    price_unit = fields.Monetary(string='Unit Price')
    subtotal = fields.Monetary(string='Subtotal')

    kit_line_ids = fields.One2many('salon.product.kit.line', 'kit_id', string='Kit Lines')

    total_price = fields.Monetary(string='Total Kit Price', compute='_compute_total_price')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.depends('kit_line_ids', 'kit_line_ids.subtotal')
    def _compute_total_price(self):
        for kit in self:
            kit.total_price = sum(kit.kit_line_ids.mapped('subtotal'))

    def action_apply_kit(self):
        """Apply kit to service, creating stock moves for products"""
        for kit in self:
            if kit.service_id and kit.kit_line_ids:
                # Create stock moves for each product in kit
                stock_location = self.env.ref('stock.stock_location_stock')
                for line in kit.kit_line_ids:
                    # Create picking or stock move
                    pass


class SalonProductKitLine(models.Model):
    _name = 'salon.product.kit.line'
    _description = 'Product Kit Line'

    kit_id = fields.Many2one('salon.product.kit', string='Kit', required=True, ondelete='cascade')

    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=1.0)

    # price_unit = fields.Monetary(string='Unit Price', related='product_id.lst_price')
    price_unit = fields.Monetary(string='Unit Price')
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='kit_id.currency_id')

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than 0.'))
