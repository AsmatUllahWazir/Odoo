from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ClientFloorLine(models.Model):
    _name = 'client.floor.line'
    _description = 'Client Floor Assignment'
    _rec_name = 'floor_id'  # Changed from 'unit_id' to 'floor_id'

    host_company_id = fields.Many2one('client.floor', string='Client', required=True, tracking=True)
    company_representative = fields.Many2one('res.users', string='Representative (User)', tracking=True)
    company_representative_1 = fields.Many2one('res.partner', string='Representative (Partner)', tracking=True)
    floor_id = fields.Many2one('building.floor', string='Floor', required=True, tracking=True,
                               domain="[('id', 'in', possible_floor_ids)]")

    possible_representative_ids = fields.Many2many(
        'res.users',
        compute='_compute_possible_representative_ids',
        search='_search_possible_representative_ids'
    )

    possible_representative_ids_1 = fields.Many2many(
        'res.partner',
        compute='_compute_possible_representative_ids_1',
        search='_search_possible_representative_ids_1'
    )

    possible_floor_ids = fields.Many2many(
        'building.floor',
        compute='_compute_possible_floors'
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
            if record.floor_id:
                existing = self.search([
                    ('floor_id', '=', record.floor_id.id),
                    ('id', '!=', record.id),
                    ('host_company_id', '!=', record.host_company_id.id)
                ], limit=1)

                if existing:
                    raise ValidationError(
                        f"Floor {record.floor_id.name} is already assigned to {existing.host_company_id.name}!"
                    )

    @api.constrains('floor_id', 'host_company_id')
    def _check_floor_not_in_other_company(self):
        for line in self:
            if line.floor_id:
                other_companies = self.env['client.floor'].search([
                    ('id', '!=', line.host_company_id.id),
                    ('floor_ids', 'in', line.floor_id.id)
                ])
                if other_companies:
                    raise ValidationError(
                        f"Floor {line.floor_id.name} is already assigned to client: {other_companies[0].name}"
                    )
