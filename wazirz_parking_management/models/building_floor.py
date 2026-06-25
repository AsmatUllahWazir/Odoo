from odoo import models, fields, api


class BuildingFloor(models.Model):
    _name = 'building.floor'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Building Floors'
    _rec_name = 'name'

    name = fields.Char('Floor Number/Name', required=True, tracking=True)
    active = fields.Boolean(default=True)
    parking_spaces = fields.Integer('Total Parking Spaces', tracking=True)
    valet = fields.Integer('Valet Spaces', tracking=True)
    valet_plus = fields.Integer('Valet+ Spaces', tracking=True)
    description = fields.Text('Description')
    location_id = fields.Many2one('floor.location', string='Floor Location')
    # access_card_limit = fields.Integer('Access Card Limit', tracking=True)

    # Fixed: Changed from 'unit_id' to 'floor_id' to match new naming
    car_parking_ids = fields.One2many(
        'car.parking',
        'floor_id',
        string='Parking Records'
    )

    host_company_id = fields.Many2one(
        'client.floor',
        string='Assigned Client',
        compute='_compute_host_company',
        store=True,
    )

    host_company_image = fields.Binary(
        string='Company Logo',
        related='host_company_id.company_image',
        store=False,
        readonly=True,
    )

    used_normal_parking = fields.Integer(
        string='Used Normal Parking',
        compute='_compute_parking_stats',
        store=True
    )

    used_valet_parking = fields.Integer(
        string='Used Valet Parking',
        compute='_compute_parking_stats',
        store=True
    )

    used_parking_spaces = fields.Integer(
        string='Used Parking (Normal/Valet Combined)',
        compute='_compute_parking_stats',
        store=True
    )

    remaining_parking_spaces = fields.Integer(
        string='Remaining Parking (Normal/Valet)',
        compute='_compute_parking_stats',
        store=True
    )

    total_valet_plus = fields.Integer(
        string='Total Valet+',
        compute='_compute_total_capacity',
        store=True
    )

    used_valet_plus = fields.Integer(
        string='Used Valet+',
        compute='_compute_valet_plus_stats',
        store=True
    )

    remaining_valet_plus = fields.Integer(
        string='Remaining Valet+',
        compute='_compute_valet_plus_stats',
        store=True
    )

    # Fixed: Changed field name to match new naming
    host_company_line_ids = fields.One2many(
        'client.floor.line',
        'floor_id',
        string='Client Assignments',
        readonly=True
    )

    is_assigned = fields.Boolean(
        string='Is Assigned to Client',
        compute='_compute_is_assigned',
        search='_search_is_assigned'
    )

    # used_access_cards = fields.Integer(
    #     string='Used Access Cards',
    #     compute='_compute_access_card_stats',
    #     store=True
    # )
    #
    # remaining_access_cards = fields.Integer(
    #     string='Remaining Access Cards',
    #     compute='_compute_access_card_stats',
    #     store=True
    # )
    #
    # @api.depends('access_card_ids', 'access_card_ids.state', 'access_card_limit')
    # def _compute_access_card_stats(self):
    #     for floor in self:
    #         used_access_cards = floor.access_card_ids.filtered(
    #             lambda c: c.state not in ('canceled', 'lost', 'expired')
    #         )
    #         floor.used_access_cards = len(used_access_cards)
    #         floor.remaining_access_cards = max(0, (floor.access_card_limit or 0) - floor.used_access_cards)

    @api.depends('host_company_line_ids.host_company_id')
    def _compute_host_company(self):
        for floor in self:
            host_company_line = self.env['client.floor.line'].search([
                ('floor_id', '=', floor.id)
            ], limit=1)

            if host_company_line:
                floor.host_company_id = host_company_line.host_company_id
            else:
                floor.host_company_id = False

    @api.depends('car_parking_ids', 'car_parking_ids.state', 'car_parking_ids.parking_type')
    def _compute_parking_stats(self):
        for floor in self:
            used_normal = floor.car_parking_ids.filtered(
                lambda p: p.parking_type == 'normal' and p.state not in ('canceled', 'archive')
            )
            floor.used_normal_parking = len(used_normal)

            used_valet = floor.car_parking_ids.filtered(
                lambda p: p.parking_type == 'valet' and p.state not in ('canceled', 'archive')
            )
            floor.used_valet_parking = len(used_valet)

            floor.used_parking_spaces = floor.used_normal_parking + floor.used_valet_parking
            floor.remaining_parking_spaces = max(0, (floor.parking_spaces or 0) - floor.used_parking_spaces)

    @api.depends('car_parking_ids', 'car_parking_ids.state', 'car_parking_ids.parking_type')
    def _compute_valet_plus_stats(self):
        for floor in self:
            used_valet_plus = floor.car_parking_ids.filtered(
                lambda p: p.parking_type == 'valet_pl' and p.state not in ('canceled', 'archive')
            )
            floor.used_valet_plus = len(used_valet_plus)
            floor.remaining_valet_plus = max(0, (floor.valet_plus or 0) - floor.used_valet_plus)

    @api.depends('parking_spaces', 'valet_plus')
    def _compute_total_capacity(self):
        for floor in self:
            floor.total_valet_plus = floor.valet_plus or 0

    def _compute_is_assigned(self):
        assigned_floor_ids = self.env['client.floor.line'].search([]).mapped('floor_id.id')
        assigned_set = set(assigned_floor_ids)

        for floor in self:
            floor.is_assigned = floor.id in assigned_set

    def _search_is_assigned(self, operator, value):
        if operator == '=' and value is True:
            assigned_floor_ids = self.env['client.floor.line'].search([]).mapped('floor_id.id')
            return [('id', 'in', assigned_floor_ids)]
        elif operator == '=' and value is False:
            assigned_floor_ids = self.env['client.floor.line'].search([]).mapped('floor_id.id')
            return [('id', 'not in', assigned_floor_ids)]
        else:
            return []
