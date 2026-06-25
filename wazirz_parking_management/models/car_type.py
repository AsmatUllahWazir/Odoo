from odoo import models, fields


class CarType(models.Model):
    _name = 'car.type'
    _description = 'Car Type'
    _rec_name = 'name'

    name = fields.Char('Car Type', required=True)
    code = fields.Char('Type Code')
    description = fields.Text('Description')
    active = fields.Boolean(default=True)
