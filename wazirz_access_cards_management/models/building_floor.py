from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BuildingFloor(models.Model):
    _name = 'building.floor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Building Floor'
    _rec_name = 'floor_number'
    _order = 'building_name, floor_number'

    # Basic Information
    floor_number = fields.Char(
        string='Floor Number',
        required=True,
        tracking=True
    )
    building_name = fields.Char(
        string='Building Name',
        required=True,
        tracking=True
    )
    floor_description = fields.Text(
        string='Description',
        tracking=True
    )

    # Capacity and Limits
    floor_area = fields.Float(
        string='Area (sqm)',
        tracking=True
    )
    capacity = fields.Integer(
        string='Capacity',
        default=100,
        tracking=True
    )
    access_card_limit = fields.Integer(
        string='Access Card Limit',
        default=50,
        tracking=True,
        help='Maximum number of active access cards allowed for this floor'
    )

    # Status
    active = fields.Boolean(
        string='Active',
        default=True
    )

    # Relations
    client_ids = fields.Many2many(
        'client.floor',
        string='Clients'
    )
    access_card_ids = fields.One2many(
        'access.card',
        'unit_id',
        string='Access Cards'
    )

    # Computed Fields
    access_card_count = fields.Integer(
        compute='_compute_access_card_stats',
        string='Total Cards'
    )
    active_card_count = fields.Integer(
        compute='_compute_access_card_stats',
        string='Active Cards'
    )
    available_spaces = fields.Integer(
        compute='_compute_available_spaces',
        string='Available Spaces'
    )
    usage_percentage = fields.Float(
        compute='_compute_usage_percentage',
        string='Usage (%)'
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        readonly=True
    )

    @api.depends('access_card_ids')
    def _compute_access_card_stats(self):
        for floor in self:
            floor.access_card_count = len(floor.access_card_ids)
            floor.active_card_count = len(floor.access_card_ids.filtered(
                lambda c: c.state in ['active', 'management_approval', 'tech_active']
            ))

    @api.depends('access_card_limit', 'active_card_count')
    def _compute_available_spaces(self):
        for floor in self:
            floor.available_spaces = max(0, floor.access_card_limit - floor.active_card_count)

    @api.depends('access_card_limit', 'active_card_count')
    def _compute_usage_percentage(self):
        for floor in self:
            if floor.access_card_limit > 0:
                floor.usage_percentage = (floor.active_card_count / floor.access_card_limit) * 100
            else:
                floor.usage_percentage = 0

    @api.constrains('floor_number', 'building_name')
    def _check_unique_floor(self):
        for record in self:
            existing = self.search([
                ('floor_number', '=', record.floor_number),
                ('building_name', '=', record.building_name),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(_(
                    "Floor %(floor)s in building %(building)s already exists!",
                    floor=record.floor_number,
                    building=record.building_name
                ))

    @api.constrains('access_card_limit')
    def _check_access_card_limit(self):
        for floor in self:
            if floor.access_card_limit < floor.active_card_count:
                raise ValidationError(_(
                    "Cannot reduce access card limit below current active cards count (%(count)s).",
                    count=floor.active_card_count
                ))

    @api.model
    def name_create(self, name):
        return self.create({'floor_number': name, 'building_name': name}).name_get()[0]

    def name_get(self):
        res = []
        for floor in self:
            name = f"{floor.building_name} - Floor {floor.floor_number}"
            if floor.floor_area:
                name += f" ({floor.floor_area} sqm)"
            res.append((floor.id, name))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('building_name', operator, name), ('floor_number', operator, name)]
            if operator in ('=', 'like', 'ilike'):
                domain = ['|', ('building_name', 'ilike', name), ('floor_number', 'ilike', name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

    def action_view_access_cards(self):
        self.ensure_one()
        return {
            'name': _('Access Cards'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'access.card',
            'domain': [('unit_id', '=', self.id)],
            'context': {
                'default_unit_id': self.id,
                'create': True,
                'edit': True,
                'delete': True,
            },
        }
    