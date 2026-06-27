from odoo import models, fields, _


class AccessCardType(models.Model):
    _name = 'access.card.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Personal Card Type'
    _rec_name = 'name'

    name = fields.Char(
        string='Type Name',
        required=True,
        tracking=True
    )
    code = fields.Char(
        string='Code',
        required=True,
        tracking=True
    )
    description = fields.Text(
        string='Description',
        tracking=True
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    