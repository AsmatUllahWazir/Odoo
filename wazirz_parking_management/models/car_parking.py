from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime


class CarParking(models.Model):
    _name = 'car.parking'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Car Parking Request"
    _order = 'state_order asc, emp_name asc'

    name = fields.Char(string='Reference', copy=False,
                       default=lambda self: self.env['ir.sequence'].next_by_code('car.parking.id') or 'New')

    host_cmp_id = fields.Many2one('client.floor', string='Client', tracking=True,
                                  domain="[('partner_id', '!=', False)]")
    host_company_id = fields.Many2one('res.partner', string='Host Contact', tracking=True,
                                      domain=[('is_host_comp', '=', True)])

    emp_id = fields.Many2one('res.users', string="Employee", tracking=True)
    emp_name = fields.Char("Employee Name", required=True, tracking=True)
    emp_internal_no = fields.Char("Employee ID", tracking=True)
    emp_phone = fields.Char("Phone Number", tracking=True)
    emp_email = fields.Char("Email", tracking=True)

    # License Plate fields - enhanced with validation
    number_plate_digits = fields.Char("Plate Digits")
    number_plate_alphabets = fields.Char("Plate Alphabets")
    car_color = fields.Char("Car Color", tracking=True)
    car_model = fields.Char("Car Model", tracking=True)
    tag = fields.Char("Tag", tracking=True)

    time_in = fields.Datetime('Time In', default=fields.Datetime.now)
    time_out = fields.Datetime('Time Out', default=fields.Datetime.now)

    parent_id = fields.Many2one("car.parking", "Previous Record", tracking=True)
    parent_ids = fields.Many2many('car.parking', 'car_parking_self_rel', 'parent_id', 'child_id',
                                  string="Previous Records", tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('management_approval', 'Management Review'),
        ('tech_active', 'Technical Review'),
        ('active', 'Active'),
        ('edit', 'Edit'),
        ('canceled', 'Canceled'),
        ('disable', 'Disable Request'),
        ('archive', 'Archived'),
        ('rejected', 'Rejected'),
        ('blocked', 'Blocked'),
    ], string='Status', required=True, copy=False, tracking=True, default='draft')

    active = fields.Boolean(default=True)

    available_floor_ids = fields.Many2many(
        'building.floor',
        compute='_compute_available_floors',
        store=False
    )

    floor_id = fields.Many2one(
        'building.floor',
        tracking=True,
        string='Floor/Unit',
        required=True,
        domain="[('id', 'in', available_floor_ids)]"
    )

    parking_type = fields.Selection([
        ('normal', 'Normal Parking'),
        ('valet', 'Valet'),
        ('valet_pl', 'Valet+')
    ], string='Parking Type', default='normal', required=True, tracking=True)

    car_type_id = fields.Many2one('car.type', string='Car Type', tracking=True)

    state_order = fields.Integer(
        string='State Order',
        compute='_compute_state_order',
        store=True,
        index=True
    )

    # Parking capacity fields
    total_parking_spaces = fields.Integer(
        string='Total Parking Spaces',
        compute='_compute_total_capacity',
        store=True
    )

    total_valet_plus = fields.Integer(
        string='Total Valet+',
        compute='_compute_total_capacity',
        store=True
    )

    used_normal_parking = fields.Integer(
        string='Used Normal Parking',
        compute='_compute_parking_stats',
        store=True
    )

    used_valet_parking = fields.Integer(
        string='Used Valet',
        compute='_compute_parking_stats',
        store=True
    )

    used_parking_spaces = fields.Integer(
        string='Used Parking (Normal/Valet)',
        compute='_compute_parking_stats',
        store=True
    )

    remaining_parking_spaces = fields.Integer(
        string='Remaining Parking Spaces',
        compute='_compute_parking_stats',
        store=True
    )

    used_valet_plus = fields.Integer(
        string='Used Valet+',
        compute='_compute_parking_stats',
        store=True
    )

    remaining_valet_plus = fields.Integer(
        string='Remaining Valet+',
        compute='_compute_parking_stats',
        store=True
    )

    # Rejection and Block fields
    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)
    block_reason = fields.Text(string='Block Reason', tracking=True)
    rejected_by = fields.Many2one('res.users', string='Rejected By', tracking=True)
    rejected_date = fields.Datetime(string='Rejected Date', tracking=True)
    blocked_by = fields.Many2one('res.users', string='Blocked By', tracking=True)
    blocked_date = fields.Datetime(string='Blocked Date', tracking=True)
    unblocked_by = fields.Many2one('res.users', string='Unblocked By', tracking=True)
    unblocked_date = fields.Datetime(string='Unblocked Date', tracking=True)

    # License plate parts for Arabic/English support
    part1_1 = fields.Char('P1-1', size=1, tracking=True)
    part1_2 = fields.Char('P1-2', size=1, tracking=True)
    part1_3 = fields.Char('P1-3', size=1, tracking=True)

    part2_1 = fields.Char('P2-1', size=1, tracking=True)
    part2_2 = fields.Char('P2-2', size=1, tracking=True)
    part2_3 = fields.Char('P2-3', size=1, tracking=True)
    part2_4 = fields.Char('P2-4', size=1, tracking=True)

    part3_1 = fields.Char('P3-1', size=1, tracking=True)
    part3_2 = fields.Char('P3-2', size=1, tracking=True)
    part3_3 = fields.Char('P3-3', size=1, tracking=True)

    number_plate = fields.Char("Plate (English)", compute='_compute_plates', store=True)
    number_plate_arabic = fields.Char("Plate (Arabic)", compute='_compute_plates', store=True)

    # Arabic mapping
    EN_TO_AR = {
        'A': 'ا', 'B': 'ب', 'J': 'ج', 'D': 'د', 'R': 'ر', 'S': 'س', 'X': 'ص',
        'T': 'ط', 'E': 'ع', 'F': 'ف', 'G': 'ق', 'K': 'ك', 'L': 'ل', 'Z': 'ز',
        'N': 'ن', 'H': 'ه', 'U': 'و', 'V': 'و', 'Y': 'ي', 'W': 'و', 'Q': 'ق'
    }
    AR_TO_EN = {v: k for k, v in EN_TO_AR.items()}

    @api.depends('part1_1', 'part1_2', 'part1_3',
                 'part2_1', 'part2_2', 'part2_3', 'part2_4',
                 'part3_1', 'part3_2', 'part3_3')
    def _compute_plates(self):
        for r in self:
            eng_letters = ''.join(filter(None, [r.part1_1, r.part1_2, r.part1_3])).upper()
            digits = ''.join(filter(None, [r.part2_1, r.part2_2, r.part2_3, r.part2_4]))

            ar_parts = [r.part3_1, r.part3_2, r.part3_3]
            ar_parts_filtered = list(filter(None, ar_parts))
            ar_parts_reversed = list(reversed(ar_parts_filtered))
            ar_letters = ' '.join(ar_parts_reversed)

            r.number_plate = f"{eng_letters} {digits}".strip() if eng_letters or digits else ""
            r.number_plate_arabic = f"{digits} {ar_letters}".strip() if ar_letters or digits else ""

    @api.onchange('part3_1', 'part3_2', 'part3_3')
    def _onchange_arabic_to_english(self):
        for i, field in enumerate(['part3_1', 'part3_2', 'part3_3'], 1):
            val = getattr(self, field, False)
            if val and val in self.AR_TO_EN:
                setattr(self, f'part1_{i}', self.AR_TO_EN[val])
            elif not val:
                setattr(self, f'part1_{i}', False)

    @api.onchange('part1_1', 'part1_2', 'part1_3')
    def _onchange_english_to_arabic(self):
        for i, field in enumerate(['part1_1', 'part1_2', 'part1_3'], 1):
            val = getattr(self, field, False)
            if val:
                up = val.upper()
                if up in self.EN_TO_AR:
                    setattr(self, f'part3_{i}', self.EN_TO_AR[up])
                else:
                    setattr(self, f'part3_{i}', False)
            else:
                setattr(self, f'part3_{i}', False)

    @api.depends('state')
    def _compute_state_order(self):
        state_mapping = {
            'draft': 0,
            'submitted': 1,
            'management_approval': 2,
            'tech_active': 3,
            'active': 4,
            'edit': 5,
            'canceled': 6,
            'disable': 7,
            'archive': 8,
            'rejected': 9,
            'blocked': 10,
        }
        for record in self:
            record.state_order = state_mapping.get(record.state, 10)

    @api.depends('floor_id', 'floor_id.parking_spaces', 'floor_id.valet_plus')
    def _compute_total_capacity(self):
        for record in self:
            if record.floor_id:
                record.total_parking_spaces = record.floor_id.parking_spaces or 0
                record.total_valet_plus = record.floor_id.valet_plus or 0
            else:
                record.total_parking_spaces = 0
                record.total_valet_plus = 0

    @api.depends('floor_id', 'floor_id.parking_spaces', 'floor_id.valet_plus',
                 'floor_id.car_parking_ids', 'floor_id.car_parking_ids.state',
                 'floor_id.car_parking_ids.parking_type')
    def _compute_parking_stats(self):
        for record in self:
            if record.floor_id:
                used_normal = record.floor_id.car_parking_ids.filtered(
                    lambda p: p.parking_type == 'normal' and p.state not in ('canceled', 'archive')
                )
                record.used_normal_parking = len(used_normal)

                used_valet = record.floor_id.car_parking_ids.filtered(
                    lambda p: p.parking_type == 'valet' and p.state not in ('canceled', 'archive')
                )
                record.used_valet_parking = len(used_valet)

                record.used_parking_spaces = record.used_normal_parking + record.used_valet_parking
                record.remaining_parking_spaces = max(0, (
                            record.floor_id.parking_spaces or 0) - record.used_parking_spaces)

                used_valet_plus = record.floor_id.car_parking_ids.filtered(
                    lambda p: p.parking_type == 'valet_pl' and p.state not in ('canceled', 'archive')
                )
                record.used_valet_plus = len(used_valet_plus)
                record.remaining_valet_plus = max(0, (record.floor_id.valet_plus or 0) - record.used_valet_plus)
            else:
                record.used_normal_parking = 0
                record.used_valet_parking = 0
                record.used_parking_spaces = 0
                record.remaining_parking_spaces = 0
                record.used_valet_plus = 0
                record.remaining_valet_plus = 0

    @api.depends('host_cmp_id')
    def _compute_available_floors(self):
        for record in self:
            if record.host_cmp_id and record.host_cmp_id.floor_ids:
                record.available_floor_ids = record.host_cmp_id.floor_ids
            else:
                record.available_floor_ids = self.env['building.floor']

    @api.onchange('host_cmp_id')
    def _onchange_host_cmp_id(self):
        self.floor_id = False
        self._compute_available_floors()
        self.action_set_host_company_id()

    @api.onchange('host_cmp_id')
    def action_set_host_company_id(self):
        self.host_company_id = False
        if self.host_cmp_id:
            self.host_company_id = self.host_cmp_id.partner_id

    # State transition methods
    def action_draft(self):
        for rec in self:
            rec.active = True
            rec.state = "draft"

    def action_submit(self):
        for rec in self:
            rec.active = True
            rec.state = "submitted"

    def action_management_approve(self):
        for rec in self:
            rec.active = True
            rec.state = "management_approval"

    def action_tech_approve(self):
        for rec in self:
            rec.active = True
            rec.state = "tech_active"

    def action_activate(self):
        for rec in self:
            rec.active = True
            rec.state = "active"
            rec.message_post(
                body=_("Parking request has been activated."),
                message_type='notification'
            )

    def action_edit(self):
        for rec in self:
            rec.state = "edit"

    def action_disable_request(self):
        for rec in self:
            rec.state = "disable"

    def action_cancel(self):
        for rec in self:
            rec.state = "canceled"
            rec.active = False
            rec.message_post(
                body=_("Parking request has been canceled."),
                message_type='notification'
            )

    def action_archive(self):
        for rec in self:
            rec.active = False
            rec.state = 'archive'
            rec.message_post(
                body=_("Parking request has been archived."),
                message_type='notification'
            )

    def action_reject(self):
        """Open wizard to enter rejection reason"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rejection Reason'),
            'res_model': 'reject.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model_name': 'car.parking',
                'default_record_id': self.id,
            }
        }

    def action_execute_reject(self, reason):
        """Called from wizard to reject the record"""
        for rec in self:
            rec.write({
                'state': 'rejected',
                'rejection_reason': reason,
                'rejected_by': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
                'active': False,
            })
            rec.message_post(
                body=_("Request has been rejected. Reason: %s") % reason,
                message_type='notification'
            )

    def action_block(self):
        """Open wizard to enter block reason"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Block Reason'),
            'res_model': 'block.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model_name': 'car.parking',
                'default_record_id': self.id,
            }
        }

    def action_execute_block(self, reason):
        """Called from wizard to block the record"""
        for rec in self:
            rec.write({
                'state': 'blocked',
                'block_reason': reason,
                'blocked_by': self.env.user.id,
                'blocked_date': fields.Datetime.now(),
                'active': True,
            })
            rec.message_post(
                body=_("Access has been BLOCKED. Reason: %s") % reason,
                message_type='notification'
            )

    def action_unblock(self):
        """Restore status to Active"""
        for rec in self:
            try:
                rec._check_parking_limit_for_record({
                    'floor_id': rec.floor_id.id,
                    'parking_type': rec.parking_type,
                    'state': 'active'
                })
            except ValidationError as e:
                raise ValidationError(_(
                    "Cannot unblock this record. The parking limit has been reached. "
                    "Error: %s") % str(e))

            rec.write({
                'state': 'active',
                'unblocked_by': self.env.user.id,
                'unblocked_date': fields.Datetime.now(),
            })
            rec.message_post(
                body=_("Access has been UNBLOCKED. Previous reason: %s") % rec.block_reason,
                message_type='notification'
            )

    def action_activate_selected(self):
        """Activate selected parking records"""
        if not self:
            raise ValidationError(_("No records selected."))

        to_activate = self.filtered(lambda r: r.state != 'active')

        if not to_activate:
            raise ValidationError(_("All selected records are already active."))

        for rec in to_activate:
            try:
                rec._check_parking_limit_for_record({
                    'floor_id': rec.floor_id.id,
                    'parking_type': rec.parking_type,
                    'state': 'active'
                })
            except ValidationError as e:
                raise ValidationError(_(
                    "Cannot activate record %s. Parking limit exceeded. Error: %s") % (rec.name, str(e)))

        to_activate.write({
            'state': 'active',
            'active': True
        })

        activated_count = len(to_activate)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%s record(s) activated successfully.') % activated_count,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _get_limit_field_for_type(self):
        mapping = {
            'normal': 'parking_spaces',
            'valet': 'parking_spaces',
            'valet_pl': 'valet_plus',
        }
        return mapping.get(self.parking_type)

    def _is_combined_type(self, parking_type):
        return parking_type in ['normal', 'valet']

    def _check_parking_limit_for_record(self, record_vals):
        """Validate parking limit for a record"""
        floor_id = record_vals.get('floor_id') or self.floor_id.id
        parking_type = record_vals.get('parking_type') or self.parking_type
        state = record_vals.get('state') or self.state

        if not floor_id or not parking_type:
            return True

        if state in ['canceled', 'archive', 'rejected']:
            return True

        floor = self.env['building.floor'].browse(floor_id)
        if not floor.exists():
            return True

        limit_mapping = {
            'normal': 'parking_spaces',
            'valet': 'parking_spaces',
            'valet_pl': 'valet_plus',
        }
        limit_field = limit_mapping.get(parking_type)
        if not limit_field:
            return True

        floor_limit = floor[0][limit_field] or 0

        if self._is_combined_type(parking_type):
            domain = [
                ('floor_id', '=', floor_id),
                ('parking_type', 'in', ['normal', 'valet']),
                ('state', 'not in', ['canceled', 'archive', 'rejected']),
            ]
        else:
            domain = [
                ('floor_id', '=', floor_id),
                ('parking_type', '=', parking_type),
                ('state', 'not in', ['canceled', 'archive', 'rejected']),
            ]

        if self.id:
            domain.append(('id', '!=', self.id))

        current_count = self.search_count(domain)

        if current_count >= floor_limit:
            type_display = dict(self._fields['parking_type'].selection).get(parking_type)
            if self._is_combined_type(parking_type):
                type_display = "Normal/Valet"

            raise ValidationError(_(
                "Cannot create/update parking record!\n"
                "Limit for %s in floor '%s' is %s (currently %s used)."
            ) % (type_display, floor.display_name, floor_limit, current_count))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'floor_id' in vals and 'parking_type' in vals:
                floor_id = vals['floor_id']
                parking_type = vals['parking_type']

                if floor_id and parking_type:
                    floor = self.env['building.floor'].browse(floor_id)
                    if floor.exists():
                        limit_mapping = {
                            'normal': 'parking_spaces',
                            'valet': 'parking_spaces',
                            'valet_pl': 'valet_plus',
                        }
                        limit_field = limit_mapping.get(parking_type)

                        if limit_field:
                            floor_limit = floor[0][limit_field] or 0

                            if parking_type in ['normal', 'valet']:
                                domain = [
                                    ('floor_id', '=', floor_id),
                                    ('parking_type', 'in', ['normal', 'valet']),
                                    ('state', 'not in', ['canceled', 'archive', 'rejected']),
                                ]
                            else:
                                domain = [
                                    ('floor_id', '=', floor_id),
                                    ('parking_type', '=', parking_type),
                                    ('state', 'not in', ['canceled', 'archive', 'rejected']),
                                ]

                            current_count = self.search_count(domain)

                            if current_count >= floor_limit:
                                type_display = dict(self._fields['parking_type'].selection).get(parking_type)
                                if parking_type in ['normal', 'valet']:
                                    type_display = "Normal/Valet"

                                raise ValidationError(_(
                                    "Cannot create parking record!\n"
                                    "Limit for %s in floor '%s' is %s (currently %s used)."
                                ) % (type_display, floor.display_name, floor_limit, current_count))

        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals:
            if vals['state'] in ['draft', 'submitted', 'active']:
                vals['active'] = True
            elif vals['state'] in ['archive', 'canceled', 'rejected']:
                vals['active'] = False

        needs_validation = any(f in vals for f in ('floor_id', 'parking_type', 'state'))

        if needs_validation:
            for record in self:
                record_vals = {}
                for field in ['floor_id', 'parking_type', 'state']:
                    if field in vals:
                        record_vals[field] = vals[field]
                    else:
                        record_vals[field] = getattr(record, field, False)

                record._check_parking_limit_for_record(record_vals)

        return super().write(vals)

    @api.onchange('floor_id', 'parking_type')
    def _onchange_floor_type(self):
        if not self.floor_id or not self.parking_type:
            return {}

        limit_field = self._get_limit_field_for_type()
        if not limit_field:
            return {}

        floor_limit = getattr(self.floor_id, limit_field, 0) or 0

        if self._is_combined_type(self.parking_type):
            domain = [
                ('floor_id', '=', self.floor_id.id),
                ('parking_type', 'in', ['normal', 'valet']),
                ('state', 'not in', ['canceled', 'archive', 'rejected']),
            ]
        else:
            domain = [
                ('floor_id', '=', self.floor_id.id),
                ('parking_type', '=', self.parking_type),
                ('state', 'not in', ['canceled', 'archive', 'rejected']),
            ]

        if self.id:
            domain.append(('id', '!=', self.id))
            current_count = self.search_count(domain)
        else:
            current_count = self.env['car.parking'].search_count(domain)

        if current_count >= floor_limit:
            type_display = dict(self._fields['parking_type'].selection).get(self.parking_type)
            if self._is_combined_type(self.parking_type):
                type_display = "Normal/Valet"

            return {
                'warning': {
                    'title': _("Parking Limit Exceeded"),
                    'message': _(
                        "Cannot select this floor/type combination!\n"
                        "Limit for %s in floor '%s' is %s (currently %s used).") % (
                                   type_display,
                                   self.floor_id.display_name,
                                   floor_limit,
                                   current_count
                               )
                }
            }
        return {}
