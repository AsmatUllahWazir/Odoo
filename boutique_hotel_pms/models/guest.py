from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import re
import logging

_logger = logging.getLogger(__name__)


class HotelGuest(models.Model):
    _name = 'hotel.guest'
    _description = 'Hotel Guest'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'partner_id desc'

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Complete display name'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        help='Associated partner record'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    # Personal Information
    first_name = fields.Char(
        string='First Name',
        related='partner_id.name',
        store=True,
        help='First name'
    )
    last_name = fields.Char(
        string='Last Name',
        related='partner_id.name',
        store=True,
        help='Last name'
    )
    email = fields.Char(
        string='Email',
        related='partner_id.email',
        store=True,
        help='Email address'
    )
    phone = fields.Char(
        string='Phone',
        related='partner_id.phone',
        store=True,
        help='Phone number'
    )
    mobile = fields.Char(
        string='Mobile',
        related='partner_id.mobile',
        store=True,
        help='Mobile number'
    )
    birth_date = fields.Date(
        string='Date of Birth',
        help='Guest date of birth'
    )
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', help='Gender of the guest')
    nationality = fields.Many2one(
        'res.country',
        string='Nationality',
        help='Nationality of the guest'
    )
    language = fields.Selection(
        [('en', 'English'), ('es', 'Spanish'), ('fr', 'French'),
         ('de', 'German'), ('it', 'Italian'), ('pt', 'Portuguese'),
         ('zh', 'Chinese'), ('ja', 'Japanese'), ('ar', 'Arabic'),
         ('ru', 'Russian'), ('other', 'Other')],
        string='Preferred Language',
        default='en',
        help='Preferred language for communication'
    )

    # Identification
    id_document_type = fields.Selection([
        ('passport', 'Passport'),
        ('national_id', 'National ID'),
        ('drivers_license', 'Driver\'s License'),
        ('voter_id', 'Voter ID'),
        ('pan_card', 'PAN Card'),
        ('other', 'Other')
    ], string='ID Document Type',
        help='Type of ID document provided')
    id_document_number = fields.Char(
        string='ID Document Number',
        help='Government-issued ID number'
    )
    id_document_issue_date = fields.Date(
        string='ID Issue Date',
        help='Date of issue of ID document'
    )
    id_document_expiry_date = fields.Date(
        string='ID Expiry Date',
        help='Date of expiry of ID document'
    )
    id_document_attachment = fields.Binary(
        string='ID Document Attachment',
        attachment=True,
        help='Scanned copy of ID document'
    )
    id_verified = fields.Boolean(
        string='ID Verified',
        default=False,
        help='Whether the ID has been verified'
    )
    id_verified_date = fields.Date(
        string='ID Verified Date',
        help='Date when ID was verified'
    )
    id_verified_by = fields.Many2one(
        'res.users',
        string='ID Verified By',
        help='Staff who verified the ID'
    )

    # Guest Preferences
    preferences = fields.Text(
        string='Preferences',
        help='Guest preferences (e.g., room type, floor, pillow type, dining preferences)'
    )
    special_diet = fields.Text(
        string='Dietary Requirements',
        help='Special dietary requirements or allergies'
    )
    accessibility_needs = fields.Text(
        string='Accessibility Needs',
        help='Any accessibility requirements'
    )
    smoking_preference = fields.Selection([
        ('smoker', 'Smoker'),
        ('non_smoker', 'Non-smoker'),
        ('no_preference', 'No Preference')
    ], string='Smoking Preference',
        default='no_preference',
        help='Smoking preference')
    bed_preference = fields.Selection([
        ('single', 'Single Bed'),
        ('double', 'Double Bed'),
        ('queen', 'Queen Bed'),
        ('king', 'King Bed'),
        ('twin', 'Twin Beds'),
        ('no_preference', 'No Preference')
    ], string='Bed Preference',
        default='no_preference',
        help='Preferred bed type')
    floor_preference = fields.Integer(
        string='Floor Preference',
        help='Preferred floor number'
    )
    room_type_preference_ids = fields.Many2many(
        'hotel.room.type',
        string='Preferred Room Types',
        help='Preferred room types'
    )
    amenity_preference_ids = fields.Many2many(
        'hotel.amenity',
        string='Preferred Amenities',
        help='Preferred amenities'
    )

    # Loyalty and Membership
    loyalty_program = fields.Selection([
        ('none', 'None'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
        ('diamond', 'Diamond')
    ], string='Loyalty Program',
        default='none',
        help='Loyalty program level')
    loyalty_points = fields.Float(
        string='Loyalty Points',
        default=0.0,
        help='Accumulated loyalty points'
    )
    loyalty_member_since = fields.Date(
        string='Member Since',
        help='Date when joined loyalty program'
    )
    membership_number = fields.Char(
        string='Membership Number',
        help='Unique membership number'
    )
    membership_card = fields.Binary(
        string='Membership Card',
        attachment=True,
        help='Membership card image'
    )

    # Guest History
    total_stays = fields.Integer(
        string='Total Stays',
        compute='_compute_guest_stats',
        store=True,
        help='Total number of completed stays'
    )
    total_nights = fields.Integer(
        string='Total Nights',
        compute='_compute_guest_stats',
        store=True,
        help='Total number of nights stayed'
    )
    total_spent = fields.Monetary(
        string='Total Spent',
        compute='_compute_guest_stats',
        store=True,
        help='Total amount spent at the hotel'
    )
    average_spend = fields.Monetary(
        string='Average Spend per Stay',
        compute='_compute_guest_stats',
        store=True,
        help='Average amount spent per stay'
    )
    last_visit = fields.Date(
        string='Last Visit',
        compute='_compute_guest_stats',
        store=True,
        help='Date of last stay'
    )
    first_visit = fields.Date(
        string='First Visit',
        compute='_compute_guest_stats',
        store=True,
        help='Date of first stay'
    )
    preferred_room_type_id = fields.Many2one(
        'hotel.room.type',
        string='Preferred Room Type',
        compute='_compute_preferred_room_type',
        store=True,
        help='Most frequently booked room type'
    )
    average_rating_given = fields.Float(
        string='Average Rating Given',
        compute='_compute_guest_stats',
        store=True,
        help='Average rating given by guest'
    )
    total_reviews = fields.Integer(
        string='Total Reviews',
        compute='_compute_guest_stats',
        store=True,
        help='Total number of reviews'
    )

    # Blacklist and Security
    is_blacklisted = fields.Boolean(
        string='Blacklisted',
        default=False,
        tracking=True,
        help='Whether this guest is blacklisted'
    )
    blacklist_reason = fields.Text(
        string='Blacklist Reason',
        help='Reason for blacklisting this guest'
    )
    blacklist_date = fields.Date(
        string='Blacklist Date',
        help='Date when blacklisted'
    )
    blacklisted_by = fields.Many2one(
        'res.users',
        string='Blacklisted By',
        help='Staff who blacklisted the guest'
    )
    is_vip = fields.Boolean(
        string='VIP Guest',
        default=False,
        help='Whether this guest is a VIP'
    )
    vip_level = fields.Selection([
        ('vip', 'VIP'),
        ('vvip', 'VVIP'),
        ('celebrity', 'Celebrity'),
        ('corporate', 'Corporate')
    ], string='VIP Level',
        help='VIP level')
    vip_notes = fields.Text(
        string='VIP Notes',
        help='Special notes about VIP status'
    )
    security_notes = fields.Text(
        string='Security Notes',
        help='Security-related notes'
    )

    # Additional Fields
    emergency_contact_name = fields.Char(
        string='Emergency Contact Name',
        help='Name of emergency contact'
    )
    emergency_contact_phone = fields.Char(
        string='Emergency Contact Phone',
        help='Phone number of emergency contact'
    )
    emergency_contact_relation = fields.Char(
        string='Relationship',
        help='Relationship to emergency contact'
    )
    notes = fields.Text(
        string='Notes',
        help='General notes about the guest'
    )
    internal_notes = fields.Text(
        string='Internal Notes',
        help='Internal notes visible only to staff'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this guest record is active'
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

    @api.depends('partner_id')
    def _compute_display_name(self):
        for record in self:
            if record.partner_id:
                record.display_name = record.partner_id.name
            else:
                record.display_name = ''

    @api.depends('partner_id')
    def _compute_guest_stats(self):
        for record in self:
            reservations = self.env['hotel.reservation'].search([
                ('partner_id', '=', record.partner_id.id),
                ('state', 'in', ['checked_in', 'checked_out'])
            ])

            completed = reservations.filtered(lambda r: r.state == 'checked_out')
            record.total_stays = len(completed)
            record.total_nights = sum(completed.mapped('number_of_nights'))
            record.total_spent = sum(completed.mapped('total_amount'))

            if record.total_stays > 0:
                record.average_spend = record.total_spent / record.total_stays
            else:
                record.average_spend = 0.0

            # Last and first visit
            if completed:
                record.last_visit = max(completed.mapped('check_out_date'))
                record.first_visit = min(completed.mapped('check_in_date'))
            else:
                record.last_visit = False
                record.first_visit = False

            # Reviews and ratings
            reviews = self.env['hotel.review'].search([
                ('partner_id', '=', record.partner_id.id)
            ])
            record.total_reviews = len(reviews)
            if reviews:
                record.average_rating_given = sum(reviews.mapped('rating')) / len(reviews)
            else:
                record.average_rating_given = 0.0

    @api.depends('partner_id')
    def _compute_preferred_room_type(self):
        for record in self:
            reservations = self.env['hotel.reservation'].search([
                ('partner_id', '=', record.partner_id.id),
                ('state', '=', 'checked_out')
            ])
            if reservations:
                room_type_counts = {}
                for res in reservations:
                    for room in res.room_ids:
                        if room.room_type_id.id in room_type_counts:
                            room_type_counts[room.room_type_id.id] += 1
                        else:
                            room_type_counts[room.room_type_id.id] = 1
                if room_type_counts:
                    most_common = max(room_type_counts, key=room_type_counts.get)
                    record.preferred_room_type_id = most_common
                else:
                    record.preferred_room_type_id = False
            else:
                record.preferred_room_type_id = False

    @api.constrains('id_document_number')
    def _check_id_document(self):
        for record in self:
            if record.id_document_number:
                # Check for duplicate ID numbers
                existing = self.search([
                    ('id_document_number', '=', record.id_document_number),
                    ('id_document_type', '=', record.id_document_type),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError('This ID document number is already registered for another guest.')

    @api.constrains('id_document_expiry_date')
    def _check_id_expiry(self):
        for record in self:
            if record.id_document_expiry_date and record.id_document_expiry_date < fields.Date.today():
                raise ValidationError('The ID document has expired.')

    def action_verify_id(self):
        for record in self:
            record.id_verified = True
            record.id_verified_date = fields.Date.today()
            record.id_verified_by = self.env.user
            record.message_post(body=_('ID document verified.'))

    def action_toggle_blacklist(self):
        for record in self:
            record.is_blacklisted = not record.is_blacklisted
            if record.is_blacklisted:
                record.blacklist_date = fields.Date.today()
                record.blacklisted_by = self.env.user
                record.message_post(body=_('Guest blacklisted.'))
            else:
                record.message_post(body=_('Guest removed from blacklist.'))

    def action_toggle_vip(self):
        for record in self:
            record.is_vip = not record.is_vip
            record.message_post(body=_('VIP status toggled.'))

    def action_view_reservations(self):
        self.ensure_one()
        return {
            'name': _('Guest Reservations'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.reservation',
            'view_mode': 'tree,form,calendar',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'target': 'current',
        }

    def action_view_folios(self):
        self.ensure_one()
        return {
            'name': _('Guest Folios'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.folio',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'target': 'current',
        }

    def action_view_reviews(self):
        self.ensure_one()
        return {
            'name': _('Guest Reviews'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.review',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'target': 'current',
        }

    def action_send_vip_welcome(self):
        self.ensure_one()
        template = self.env.ref('boutique_hotel_pms.email_template_vip_welcome', False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.message_post(body=_('VIP welcome email sent.'))
        return True

    @api.model
    def get_guest_activity(self, days=30):
        """Get guest activity for the last X days"""
        date_from = fields.Date.today() - timedelta(days=days)
        reservations = self.env['hotel.reservation'].search([
            ('check_in', '>=', date_from),
            ('state', 'in', ['checked_in', 'checked_out'])
        ])

        guests = {}
        for res in reservations:
            guest_id = res.partner_id.id
            if guest_id not in guests:
                guests[guest_id] = {
                    'guest': res.partner_id,
                    'stays': 0,
                    'nights': 0,
                    'spent': 0,
                }
            guests[guest_id]['stays'] += 1
            guests[guest_id]['nights'] += res.number_of_nights
            guests[guest_id]['spent'] += res.total_amount

        return sorted(guests.values(), key=lambda x: x['nights'], reverse=True)


class HotelReview(models.Model):
    _name = 'hotel.review'
    _description = 'Hotel Review'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Guest',
        required=True,
        help='Guest who wrote the review'
    )
    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Reservation',
        help='Associated reservation'
    )
    rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars')
    ], string='Rating', required=True,
        help='Overall rating')
    rating_cleanliness = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars')
    ], string='Cleanliness Rating',
        help='Rating for cleanliness')
    rating_service = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars')
    ], string='Service Rating',
        help='Rating for service')
    rating_location = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars')
    ], string='Location Rating',
        help='Rating for location')
    rating_value = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars')
    ], string='Value Rating',
        help='Rating for value for money')
    title = fields.Char(
        string='Review Title',
        required=True,
        help='Title of the review'
    )
    content = fields.Text(
        string='Review Content',
        required=True,
        help='Detailed review text'
    )
    pros = fields.Text(
        string='Pros',
        help='Positive aspects'
    )
    cons = fields.Text(
        string='Cons',
        help='Negative aspects'
    )
    would_recommend = fields.Boolean(
        string='Would Recommend',
        default=True,
        help='Whether guest would recommend'
    )
    published = fields.Boolean(
        string='Published',
        default=False,
        help='Whether the review is published'
    )
    featured = fields.Boolean(
        string='Featured',
        default=False,
        help='Whether this is a featured review'
    )
    published_date = fields.Datetime(
        string='Published Date',
        help='Date when published'
    )
    helpful_count = fields.Integer(
        string='Helpful Votes',
        default=0,
        help='Number of helpful votes'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    def action_publish(self):
        for record in self:
            record.published = True
            record.published_date = fields.Datetime.now()
            record.message_post(body=_('Review published.'))

    def action_unpublish(self):
        for record in self:
            record.published = False
            record.message_post(body=_('Review unpublished.'))

    def action_mark_helpful(self):
        self.helpful_count += 1
        self.message_post(body=_('Marked as helpful.'))


class HotelAmenity(models.Model):
    _name = 'hotel.amenity'
    _description = 'Hotel Amenity'
    _order = 'name'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Complete display name'
    )
    name = fields.Char(
        string='Amenity',
        required=True,
        translate=True,
        help='Name of the amenity (e.g., WiFi, AC, TV)'
    )
    code = fields.Char(
        string='Code',
        help='Short code for the amenity'
    )
    category = fields.Selection([
        ('technology', 'Technology'),
        ('comfort', 'Comfort'),
        ('entertainment', 'Entertainment'),
        ('food', 'Food & Beverage'),
        ('security', 'Security'),
        ('accessibility', 'Accessibility'),
        ('view', 'View'),
        ('other', 'Other')
    ], string='Category',
        help='Category of the amenity')
    icon = fields.Char(
        string='Icon',
        help='Font awesome icon class (e.g., fa-wifi)'
    )
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of the amenity'
    )
    is_free = fields.Boolean(
        string='Free Amenity',
        default=True,
        help='Whether this amenity is free'
    )
    price = fields.Monetary(
        string='Price (if paid)',
        currency_field='currency_id',
        help='Price if this amenity is paid'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, this amenity will be hidden'
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

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.code:
                record.display_name = f"{record.code} - {record.name}"
            else:
                record.display_name = record.name

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price and record.price < 0:
                raise ValidationError('Price cannot be negative.')

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.icon:
                name = f"{record.icon} {name}"
            if record.code:
                name = f"{record.code} - {name}"
            result.append((record.id, name))
        return result


class HotelFeature(models.Model):
    _name = 'hotel.feature'
    _description = 'Hotel Feature'
    _order = 'name'

    name = fields.Char(
        string='Feature Name',
        required=True,
        translate=True,
        help='Name of the feature'
    )
    code = fields.Char(
        string='Code',
        help='Short code for the feature'
    )
    icon = fields.Char(
        string='Icon',
        help='Font awesome icon class'
    )
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )


class HotelSeason(models.Model):
    _name = 'hotel.season'
    _description = 'Hotel Season'
    _order = 'name'

    name = fields.Char(
        string='Season Name',
        required=True,
        translate=True,
        help='Name of the season'
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Short code for the season'
    )
    date_from = fields.Date(
        string='Start Date',
        required=True,
        help='Start date of the season'
    )
    date_to = fields.Date(
        string='End Date',
        required=True,
        help='End date of the season'
    )
    description = fields.Text(
        string='Description',
        help='Description of the season'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError('End date must be after start date.')


class HotelBlackoutDate(models.Model):
    _name = 'hotel.blackout.date'
    _description = 'Hotel Blackout Date'
    _order = 'date'

    room_type_id = fields.Many2one(
        'hotel.room.type',
        string='Room Type',
        help='Room type affected (if specific)'
    )
    date = fields.Date(
        string='Date',
        required=True,
        help='Blackout date'
    )
    reason = fields.Text(
        string='Reason',
        help='Reason for blackout'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    