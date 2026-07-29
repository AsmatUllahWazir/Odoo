from odoo import fields, models


class ShippingTag(models.Model):
    """Shipping Tag for categorization"""
    _name = 'shipping.tag'
    _description = 'Shipping Tag'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Tag name must be unique!')
    ]