from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ClientFloor(models.Model):
    _name = "client.floor"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Client"
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(
        string="Client Name",
        required=True,
        tracking=True
    )
    email = fields.Char(
        string="Email",
        tracking=True
    )
    phone = fields.Char(
        string="Phone",
        tracking=True
    )
    floor_ids = fields.Many2many(
        'building.floor',
        string="Assigned Floors",
        tracking=True
    )
    access_limit = fields.Integer(
        string="Access Card Limit",
        tracking=True,
        default=100
    )
    company_image = fields.Binary(
        string='Company Logo',
        attachment=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        tracking=True,
        domain=[('is_company', '=', True)]
    )
    child_ids = fields.One2many(
        related='partner_id.child_ids',
        string="Contacts"
    )
    user_ids = fields.Many2many(
        'res.users',
        compute='_compute_user_ids',
        store=False
    )
    host_company_line_ids = fields.One2many(
        'client.floor.line',
        'host_company_id',
        string='Floor Assignments',
        copy=True
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    @api.depends('partner_id', 'child_ids')
    def _compute_user_ids(self):
        for rec in self:
            rec.user_ids = self.env['res.users']
            if rec.partner_id and rec.partner_id.user_ids:
                rec.user_ids |= rec.partner_id.user_ids
            for child in rec.child_ids:
                if child.user_ids:
                    rec.user_ids |= child.user_ids

    @api.constrains('floor_ids')
    def _check_floor_assignments(self):
        for client in self:
            if client.floor_ids and client.host_company_line_ids:
                assigned_floors = client.host_company_line_ids.mapped('floor_id')
                for floor in client.floor_ids:
                    if floor not in assigned_floors:
                        raise ValidationError(_(
                            "Floor %(floor)s must be assigned through the Floor Assignments tab.",
                            floor=floor.name
                        ))

    # def action_view_parking(self):
    #     self.ensure_one()
    #     return {
    #         'name': _("Parking Records"),
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'tree,form',
    #         'res_model': 'car.parking',
    #         'domain': [('host_company_id', '=', self.partner_id.id if self.partner_id else False)],
    #         'context': {
    #             'create': False,
    #             'edit': True,
    #             'delete': False,
    #             'default_host_company_id': self.partner_id.id if self.partner_id else False
    #         },
    #     }

    def action_view_access_cards(self):
        self.ensure_one()
        return {
            'name': _("Access Cards"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'access.card',
            'domain': [('host_company_id', '=', self.partner_id.id if self.partner_id else False)],
            'context': {
                'create': False,
                'edit': True,
                'delete': False,
                'default_host_company_id': self.partner_id.id if self.partner_id else False
            },
        }

    @api.model
    def create(self, vals):
        """Create partner automatically if not provided"""
        if not vals.get('partner_id') and vals.get('name'):
            partner_vals = {
                'name': vals.get('name'),
                'email': vals.get('email'),
                'phone': vals.get('phone'),
                'is_company': True,
            }
            partner = self.env['res.partner'].create(partner_vals)
            vals['partner_id'] = partner.id
        return super(ClientFloor, self).create(vals)

    def write(self, vals):
        """Update partner if name/email/phone changes"""
        result = super(ClientFloor, self).write(vals)
        if vals.get('name') or vals.get('email') or vals.get('phone'):
            for client in self:
                if client.partner_id:
                    partner_vals = {}
                    if vals.get('name'):
                        partner_vals['name'] = vals['name']
                    if vals.get('email'):
                        partner_vals['email'] = vals['email']
                    if vals.get('phone'):
                        partner_vals['phone'] = vals['phone']
                    if partner_vals:
                        client.partner_id.write(partner_vals)
        return result
