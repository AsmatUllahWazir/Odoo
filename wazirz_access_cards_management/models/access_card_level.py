from odoo import models, fields, _


class AccessCardLevel(models.Model):
    _name = 'access.card.level'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Personal Card Level'
    _rec_name = 'name'

    name = fields.Char(
        string='Level Name',
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
