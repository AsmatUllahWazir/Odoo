from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ClientFloorLine(models.Model):
    _name = 'client.floor.line'
    _description = 'Client Floor Assignment'
    _rec_name = 'floor_id'
    _order = 'host_company_id, floor_id'

    host_company_id = fields.Many2one(
        'client.floor',
        string='Client',
        required=True,
        tracking=True
    )
    company_representative = fields.Many2one(
        'res.users',
        string='Representative (User)',
        tracking=True
    )
    company_representative_1 = fields.Many2one(
        'res.partner',
        string='Representative (Partner)',
        tracking=True
    )
    floor_id = fields.Many2one(
        'building.floor',
        string='Floor',
        required=True,
        tracking=True,
        domain="[('id', 'in', possible_floor_ids)]"
    )
    assigned_date = fields.Date(
        string='Assigned Date',
        default=fields.Date.today,
        tracking=True
    )
    notes = fields.Text(
        string='Notes',
        tracking=True
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )

    possible_representative_ids = fields.Many2many(
        'res.users',
        compute='_compute_possible_representative_ids',
        search='_search_possible_representative_ids',
        string='Possible Representatives'
    )
    possible_representative_ids_1 = fields.Many2many(
        'res.partner',
        compute='_compute_possible_representative_ids_1',
        search='_search_possible_representative_ids_1',
        string='Possible Representatives (Partner)'
    )
    possible_floor_ids = fields.Many2many(
        'building.floor',
        compute='_compute_possible_floors',
        string='Possible Floors'
    )

    @api.depends('host_company_id', 'host_company_id.floor_ids')
    def _compute_possible_floors(self):
        for line in self:
            if line.host_company_id and line.host_company_id.floor_ids:
                line.possible_floor_ids = line.host_company_id.floor_ids
            else:
                line.possible_floor_ids = False

    @api.depends('host_company_id', 'host_company_id.child_ids', 'host_company_id.child_ids.user_ids')
    def _compute_possible_representative_ids(self):
        for line in self:
            if line.host_company_id and line.host_company_id.child_ids:
                users = line.host_company_id.child_ids.mapped('user_ids')
                line.possible_representative_ids = users
            else:
                line.possible_representative_ids = False

    def _search_possible_representative_ids(self, operator, value):
        return [('id', operator, value)]

    @api.depends('host_company_id', 'host_company_id.child_ids')
    def _compute_possible_representative_ids_1(self):
        for line in self:
            if line.host_company_id and line.host_company_id.child_ids:
                line.possible_representative_ids_1 = line.host_company_id.child_ids
            else:
                line.possible_representative_ids_1 = False

    def _search_possible_representative_ids_1(self, operator, value):
        return [('id', operator, value)]

    @api.onchange('host_company_id')
    def _onchange_host_company_id(self):
        if self.host_company_id:
            return {
                'domain': {
                    'floor_id': [('id', 'in', self.host_company_id.floor_ids.ids)]
                }
            }
        return {'domain': {'floor_id': []}}

    @api.constrains('floor_id')
    def _check_floor_unique(self):
        for record in self:
            if record.floor_id and record.host_company_id:
                existing = self.search([
                    ('floor_id', '=', record.floor_id.id),
                    ('id', '!=', record.id),
                    ('host_company_id', '!=', record.host_company_id.id)
                ], limit=1)

                if existing:
                    raise ValidationError(_(
                        "Floor %(floor)s is already assigned to %(client)s!",
                        floor=record.floor_id.name,
                        client=existing.host_company_id.name
                    ))

    @api.constrains('floor_id', 'host_company_id')
    def _check_floor_not_in_other_company(self):
        for line in self:
            if line.floor_id and line.host_company_id:
                other_companies = self.env['client.floor'].search([
                    ('id', '!=', line.host_company_id.id),
                    ('floor_ids', 'in', line.floor_id.id)
                ])
                if other_companies:
                    raise ValidationError(_(
                        "Floor %(floor)s is already assigned to client: %(client)s",
                        floor=line.floor_id.name,
                        client=other_companies[0].name
                    ))

    @api.model
    def create(self, vals):
        """Ensure floor is in host company's floor_ids"""
        result = super(ClientFloorLine, self).create(vals)
        if result.host_company_id and result.floor_id:
            if result.floor_id not in result.host_company_id.floor_ids:
                result.host_company_id.write({
                    'floor_ids': [(4, result.floor_id.id)]
                })
        return result
