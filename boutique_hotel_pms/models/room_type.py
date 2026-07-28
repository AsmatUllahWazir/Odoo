from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class HotelRoomType(models.Model):
    _name = 'hotel.room.type'
    _description = 'Hotel Room Type'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(
        string='Room Type Name',
        required=True,
        tracking=True,
        translate=True,
        help='Name of the room type (e.g., Standard, Deluxe, Suite, Penthouse)'
    )
    code = fields.Char(
        string='Code',
        required=True,
        tracking=True,
        help='Short unique code for the room type (e.g., STD, DLX, STE, PH)'
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Complete display name with code'
    )
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of the room type including features and benefits'
    )
    description_website = fields.Html(
        string='Website Description',
        translate=True,
        help='Description displayed on the website booking page'
    )

    # Capacity and Pricing
    capacity_adults = fields.Integer(
        string='Max Adults',
        required=True,
        default=2,
        help='Maximum number of adults this room type can accommodate'
    )
    capacity_children = fields.Integer(
        string='Max Children',
        default=2,
        help='Maximum number of children this room type can accommodate'
    )
    capacity_total = fields.Integer(
        string='Total Capacity',
        compute='_compute_capacity',
        store=True,
        help='Total capacity (adults + children)'
    )
    extra_bed_allowed = fields.Boolean(
        string='Extra Bed Allowed',
        default=False,
        help='Whether an extra bed can be added to this room type'
    )
    extra_bed_price = fields.Monetary(
        string='Extra Bed Price',
        currency_field='currency_id',
        help='Price for an extra bed if allowed'
    )

    # Pricing
    base_price = fields.Monetary(
        string='Base Price per Night',
        currency_field='currency_id',
        required=True,
        default=100.0,
        tracking=True,
        help='Standard nightly rate for this room type'
    )
    weekend_price = fields.Monetary(
        string='Weekend Price per Night',
        currency_field='currency_id',
        help='Nightly rate for weekends (Friday and Saturday)'
    )
    peak_price = fields.Monetary(
        string='Peak Season Price',
        currency_field='currency_id',
        help='Nightly rate during peak season'
    )
    off_peak_price = fields.Monetary(
        string='Off-Peak Price',
        currency_field='currency_id',
        help='Nightly rate during off-peak season'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )
    price_discount_percent = fields.Float(
        string='Discount Percentage',
        default=0.0,
        help='Discount percentage for this room type'
    )
    minimum_stay = fields.Integer(
        string='Minimum Stay (nights)',
        default=1,
        help='Minimum number of nights required for booking'
    )
    maximum_stay = fields.Integer(
        string='Maximum Stay (nights)',
        help='Maximum number of nights allowed for booking'
    )

    # Amenities and Features
    amenities_ids = fields.Many2many(
        'hotel.amenity',
        string='Amenities',
        help='Standard amenities included in this room type'
    )
    feature_ids = fields.Many2many(
        'hotel.feature',
        string='Features',
        help='Special features of this room type'
    )
    image_ids = fields.One2many(
        'ir.attachment',
        compute='_compute_images',
        string='Images'
    )
    image_count = fields.Integer(
        string='Image Count',
        compute='_compute_images',
        help='Number of images for this room type'
    )
    main_image = fields.Binary(
        string='Main Image',
        attachment=True,
        help='Main image for the room type'
    )
    main_image_url = fields.Char(
        string='Main Image URL',
        compute='_compute_main_image_url',
        help='URL of the main image'
    )

    # Room Statistics
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='If unchecked, this room type will be hidden from selection'
    )
    total_rooms = fields.Integer(
        string='Total Rooms',
        compute='_compute_room_stats',
        store=True,
        help='Total number of rooms of this type'
    )
    available_rooms = fields.Integer(
        string='Available Now',
        compute='_compute_room_stats',
        store=True,
        help='Number of currently available rooms'
    )
    occupied_rooms = fields.Integer(
        string='Occupied Now',
        compute='_compute_room_stats',
        store=True,
        help='Number of currently occupied rooms'
    )
    dirty_rooms = fields.Integer(
        string='Dirty Rooms',
        compute='_compute_room_stats',
        store=True,
        help='Number of rooms currently marked as dirty'
    )
    maintenance_rooms = fields.Integer(
        string='Maintenance',
        compute='_compute_room_stats',
        store=True,
        help='Number of rooms under maintenance'
    )
    blocked_rooms = fields.Integer(
        string='Blocked Rooms',
        compute='_compute_room_stats',
        store=True,
        help='Number of blocked rooms'
    )
    occupancy_rate = fields.Float(
        string='Occupancy Rate (%)',
        compute='_compute_occupancy_rate',
        store=True,
        help='Current occupancy rate for this room type'
    )
    utilization_rate = fields.Float(
        string='Utilization Rate (%)',
        compute='_compute_utilization_rate',
        store=True,
        help='Room utilization rate over time'
    )

    # Revenue and Financial
    revenue_today = fields.Monetary(
        string='Today\'s Revenue',
        compute='_compute_revenue',
        store=True,
        help='Revenue generated today from this room type'
    )
    revenue_week = fields.Monetary(
        string='This Week\'s Revenue',
        compute='_compute_revenue',
        store=True,
        help='Revenue generated this week'
    )
    revenue_month = fields.Monetary(
        string='This Month\'s Revenue',
        compute='_compute_revenue',
        store=True,
        help='Revenue generated this month'
    )
    revenue_year = fields.Monetary(
        string='This Year\'s Revenue',
        compute='_compute_revenue',
        store=True,
        help='Revenue generated this year'
    )
    average_daily_rate = fields.Monetary(
        string='Average Daily Rate',
        compute='_compute_revenue',
        store=True,
        help='Average daily rate for this room type'
    )
    revenue_per_available_room = fields.Monetary(
        string='RevPAR',
        compute='_compute_revenue',
        store=True,
        help='Revenue per available room'
    )

    # Season and Date Specific
    season_ids = fields.Many2many(
        'hotel.season',
        string='Seasons',
        help='Seasons when this room type is available'
    )
    blackout_dates = fields.One2many(
        'hotel.blackout.date',
        'room_type_id',
        string='Blackout Dates',
        help='Dates when this room type is not available'
    )

    # Additional Fields
    color = fields.Integer(
        string='Color',
        default=1,
        help='Color for Kanban views'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of display'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user
    )
    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now
    )
    last_modified_by = fields.Many2one(
        'res.users',
        string='Last Modified By',
        tracking=True
    )
    last_modified_date = fields.Datetime(
        string='Last Modified Date',
        tracking=True
    )

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.code} - {record.name}"

    @api.depends('capacity_adults', 'capacity_children')
    def _compute_capacity(self):
        for record in self:
            record.capacity_total = record.capacity_adults + record.capacity_children

    @api.depends('name')
    def _compute_images(self):
        for record in self:
            images = self.env['ir.attachment'].search([
                ('res_model', '=', 'hotel.room.type'),
                ('res_id', '=', record.id),
                ('mimetype', 'ilike', 'image/')
            ])
            record.image_ids = images
            record.image_count = len(images)

    @api.depends('main_image')
    def _compute_main_image_url(self):
        for record in self:
            if record.main_image:
                record.main_image_url = f"/web/image/hotel.room.type/{record.id}/main_image"
            else:
                record.main_image_url = False

    @api.depends('name')
    def _compute_room_stats(self):
        for record in self:
            rooms = self.env['hotel.room'].search([
                ('room_type_id', '=', record.id),
                ('active', '=', True)
            ])
            record.total_rooms = len(rooms)
            record.available_rooms = len(rooms.filtered(lambda r: r.status == 'available'))
            record.occupied_rooms = len(rooms.filtered(lambda r: r.status == 'occupied'))
            record.dirty_rooms = len(rooms.filtered(lambda r: r.status == 'dirty'))
            record.maintenance_rooms = len(rooms.filtered(lambda r: r.status == 'maintenance'))
            record.blocked_rooms = len(rooms.filtered(lambda r: r.status == 'blocked'))

    @api.depends('total_rooms', 'occupied_rooms')
    def _compute_occupancy_rate(self):
        for record in self:
            if record.total_rooms > 0:
                record.occupancy_rate = (record.occupied_rooms / record.total_rooms) * 100
            else:
                record.occupancy_rate = 0.0

    @api.depends('total_rooms', 'occupied_rooms')
    def _compute_utilization_rate(self):
        for record in self:
            if record.total_rooms > 0:
                # Calculate utilization over the past 30 days
                today = fields.Date.today()
                start_date = today - timedelta(days=30)
                reservations = self.env['hotel.reservation'].search([
                    ('room_ids.room_type_id', '=', record.id),
                    ('state', 'in', ['checked_in', 'checked_out']),
                    ('check_in', '>=', start_date),
                    ('check_in', '<=', today)
                ])
                total_nights = sum(reservations.mapped('number_of_nights'))
                max_possible_nights = record.total_rooms * 30
                record.utilization_rate = (total_nights / max_possible_nights * 100) if max_possible_nights > 0 else 0.0
            else:
                record.utilization_rate = 0.0

    @api.depends('name')
    def _compute_revenue(self):
        for record in self:
            today = fields.Date.today()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            year_start = today.replace(month=1, day=1)

            rooms = self.env['hotel.room'].search([('room_type_id', '=', record.id)])

            # Today's revenue
            today_reservations = self.env['hotel.reservation'].search([
                ('room_ids', 'in', rooms.ids),
                ('state', 'in', ['checked_in', 'checked_out']),
                ('check_in', '<=', today),
                ('check_out', '>', today)
            ])
            record.revenue_today = sum(today_reservations.mapped('total_amount'))

            # Week revenue
            week_reservations = self.env['hotel.reservation'].search([
                ('room_ids', 'in', rooms.ids),
                ('state', 'in', ['checked_in', 'checked_out']),
                ('check_in', '>=', week_start),
                ('check_in', '<=', today)
            ])
            record.revenue_week = sum(week_reservations.mapped('total_amount'))

            # Month revenue
            month_reservations = self.env['hotel.reservation'].search([
                ('room_ids', 'in', rooms.ids),
                ('state', 'in', ['checked_in', 'checked_out']),
                ('check_in', '>=', month_start),
                ('check_in', '<=', today)
            ])
            record.revenue_month = sum(month_reservations.mapped('total_amount'))

            # Year revenue
            year_reservations = self.env['hotel.reservation'].search([
                ('room_ids', 'in', rooms.ids),
                ('state', 'in', ['checked_in', 'checked_out']),
                ('check_in', '>=', year_start),
                ('check_in', '<=', today)
            ])
            record.revenue_year = sum(year_reservations.mapped('total_amount'))

            # Average Daily Rate
            if record.total_rooms > 0:
                record.average_daily_rate = record.revenue_today / record.total_rooms if record.total_rooms > 0 else 0
                record.revenue_per_available_room = record.revenue_today / record.total_rooms if record.total_rooms > 0 else 0
            else:
                record.average_daily_rate = 0.0
                record.revenue_per_available_room = 0.0

    @api.constrains('capacity_adults', 'capacity_children')
    def _check_capacity(self):
        for record in self:
            if record.capacity_adults < 1:
                raise ValidationError('Maximum adults must be at least 1.')
            if record.capacity_children < 0:
                raise ValidationError('Maximum children cannot be negative.')
            if record.capacity_total > 10:
                raise ValidationError('Total capacity cannot exceed 10 guests.')

    @api.constrains('base_price', 'weekend_price', 'peak_price', 'off_peak_price')
    def _check_prices(self):
        for record in self:
            if record.base_price < 0:
                raise ValidationError('Base price cannot be negative.')
            if record.weekend_price and record.weekend_price < 0:
                raise ValidationError('Weekend price cannot be negative.')
            if record.peak_price and record.peak_price < 0:
                raise ValidationError('Peak season price cannot be negative.')
            if record.off_peak_price and record.off_peak_price < 0:
                raise ValidationError('Off-peak price cannot be negative.')
            if record.price_discount_percent < 0 or record.price_discount_percent > 100:
                raise ValidationError('Discount percentage must be between 0 and 100.')

    @api.constrains('minimum_stay', 'maximum_stay')
    def _check_stay_duration(self):
        for record in self:
            if record.minimum_stay < 1:
                raise ValidationError('Minimum stay must be at least 1 night.')
            if record.maximum_stay and record.maximum_stay < record.minimum_stay:
                raise ValidationError('Maximum stay cannot be less than minimum stay.')

    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            existing = self.search([('code', '=', record.code), ('id', '!=', record.id)])
            if existing:
                raise ValidationError(f'Room type code "{record.code}" must be unique!')

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.code} - {record.name}"
            if record.total_rooms > 0:
                name += f" ({record.available_rooms}/{record.total_rooms})"
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        domain += args
        return self.search(domain, limit=limit).name_get()

    def action_view_rooms(self):
        """Open rooms of this type"""
        self.ensure_one()
        return {
            'name': f'Rooms - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.room',
            'view_mode': 'tree,form,kanban',
            'domain': [('room_type_id', '=', self.id)],
            'context': {'default_room_type_id': self.id},
            'target': 'current',
        }

    def action_view_reservations(self):
        """Open reservations for this room type"""
        self.ensure_one()
        rooms = self.env['hotel.room'].search([('room_type_id', '=', self.id)])
        return {
            'name': f'Reservations - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reservation',
            'view_mode': 'tree,form,calendar',
            'domain': [('room_ids', 'in', rooms.ids)],
            'target': 'current',
        }

    def action_toggle_active(self):
        """Toggle active status"""
        for record in self:
            record.active = not record.active
