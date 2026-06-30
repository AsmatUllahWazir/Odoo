# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class SalonService(models.Model):
    _name = 'salon.service'
    _description = 'Salon Service'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Service Name', required=True, tracking=True)
    description = fields.Text(string='Description', translate=True)
    service_code = fields.Char(string='Service Code', required=True, copy=False)

    category_id = fields.Many2one('salon.service.category', string='Category', required=True)
    sub_category_ids = fields.Many2many('salon.service.category', string='Sub Categories',
                                        domain="[('parent_id', '=', category_id)]")

    duration = fields.Float(string='Duration (Minutes)', required=True, default=30)
    buffer_time = fields.Float(string='Buffer Time (Minutes)', default=15,
                               help='Time between appointments for preparation')

    price = fields.Monetary(string='Price', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    member_price = fields.Monetary(string='Member Price', currency_field='currency_id')
    commission_percentage = fields.Float(string='Commission %', default=0)

    product_ids = fields.Many2many('product.product', string='Consumable Products')

    assigned_employee_ids = fields.Many2many('hr.employee', string='Assigned Staff',
                                             help='Staff qualified to perform this service')

    requires_chair = fields.Boolean(string='Requires Chair', default=True)
    requires_room = fields.Boolean(string='Requires Room', default=False)

    active = fields.Boolean(string='Active', default=True)
    is_package = fields.Boolean(string='Is Package', default=False)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.constrains('duration')
    def _check_duration(self):
        for record in self:
            if record.duration <= 0:
                raise ValidationError(_('Duration must be greater than 0 minutes.'))

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price < 0:
                raise ValidationError(_('Price cannot be negative.'))

    def get_total_duration(self):
        """Returns total duration including buffer time"""
        return self.duration + self.buffer_time


class SalonServiceCategory(models.Model):
    _name = 'salon.service.category'
    _description = 'Service Category'
    _parent_name = "parent_id"
    _parent_store = True
    _order = 'complete_name'

    name = fields.Char(string='Name', required=True, translate=True)
    parent_id = fields.Many2one('salon.service.category', string='Parent Category',
                                ondelete='cascade')
    child_ids = fields.One2many('salon.service.category', 'parent_id', string='Children')
    parent_path = fields.Char(index=True, unaccent=False)
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name',
                                store=True)

    description = fields.Text(string='Description', translate=True)
    active = fields.Boolean(string='Active', default=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name
                