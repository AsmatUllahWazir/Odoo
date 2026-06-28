from odoo import models, fields


class FloorLocation(models.Model):
    _name = 'floor.location'
    _description = 'Floor Location'
    _rec_name = 'name'

    name = fields.Char('Location Name', required=True)
    code = fields.Char('Location Code')
    description = fields.Text('Description')
    active = fields.Boolean(default=True)