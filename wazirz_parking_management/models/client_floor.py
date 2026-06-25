from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ClientFloor(models.Model):
    _name = "client.floor"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Client"
    _rec_name = 'name'

    name = fields.Char("Client Name", required=True, tracking=True)
    email = fields.Char("Email", tracking=True)
    phone = fields.Char("Phone", tracking=True)
    floor_ids = fields.Many2many('building.floor', string="Assigned Floors", tracking=True)
    access_limit = fields.Integer("Access Card Limit", tracking=True)

    company_image = fields.Binary('Company Logo')

    partner_id = fields.Many2one('res.partner', string='Related Partner', tracking=True)
    child_ids = fields.One2many(related='partner_id.child_ids', string="Contacts")
    user_ids = fields.Many2many('res.users', compute='_compute_user_ids')

    host_company_line_ids = fields.One2many('client.floor.line', 'host_company_id')

    @api.depends('partner_id', 'child_ids')
    def _compute_user_ids(self):
        for rec in self:
            rec.user_ids = self.env['res.users']
            if rec.partner_id and rec.partner_id.user_ids:
                rec.user_ids |= rec.partner_id.user_ids
            for child in rec.child_ids:
                if child.user_ids:
                    rec.user_ids |= child.user_ids

    def action_view_parking(self):
        return {
            'name': "Parking Records",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'car.parking',
            'domain': [('host_company_id', '=', self.partner_id.id)],
            'context': {'create': False, 'edit': True, 'delete': False},
        }

    def action_view_access_cards(self):
        return {
            'name': "Access Cards",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'access.card',
            'domain': [('host_company_id', '=', self.partner_id.id)],
            'context': {'create': False, 'edit': True, 'delete': False},
        }
