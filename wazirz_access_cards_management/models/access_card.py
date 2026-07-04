from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccessCard(models.Model):
    _name = 'access.card'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Personal Card"
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(
        string='Card Number',
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('access.card.id')
    )
    host_comp_id = fields.Many2one(
        'client.floor',
        string='Client',
        tracking=True,
        domain="[('partner_id', '!=', False)]"
    )
    host_company_id = fields.Many2one(
        'res.partner',
        string='Host Contact',
        tracking=True,
        domain=[('is_company', '=', True)]
    )
    emp_name = fields.Char(
        string="Employee Name",
        required=True,
        tracking=True
    )
    emp_phone = fields.Char(
        string="Employee Mobile",
        required=True,
        tracking=True
    )
    emp_email = fields.Char(
        string="Employee Email",
        tracking=True
    )
    card_no = fields.Char(
        string="Card Number",
        tracking=True
    )
    request_date = fields.Date(
        string="Request Date",
        default=fields.Date.today,
        tracking=True
    )
    issued_date = fields.Date(
        string="Issued Date",
        tracking=True
    )
    expiry_date = fields.Date(
        string="Expiry Date",
        tracking=True
    )
    received_date = fields.Date(
        string="Received Date",
        tracking=True
    )
    card_level_id = fields.Many2one(
        "access.card.level",
        string="Card Level",
        tracking=True
    )
    card_type_id = fields.Many2one(
        "access.card.type",
        string="Card Type",
        tracking=True
    )
    access_parent_id = fields.Many2one(
        "access.card",
        string="Reissued from",
        tracking=True
    )
    access_parent_ids = fields.Many2many(
        "access.card",
        'ir_model_access_card_self_rel',
        'access_parent_id',
        string="Old Cards",
        tracking=True
    )
    old_count = fields.Integer(
        compute='_compute_old_count_access',
        string='History Count'
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    state = fields.Selection([
        ('draft', 'Requested'),
        ('management_approval', 'Management Review'),
        ('tech_active', 'Technical Active'),
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('disable', 'Request to Disable'),
        ('archive', 'Archived'),
        ('rejected', 'Rejected'),
        ('blocked', 'Blocked'),
    ], string='Status', required=True, copy=False, tracking=True, default='draft')

    available_unit_ids = fields.Many2many(
        'building.floor',
        compute='_compute_available_units',
        store=False,
        string="Available Floors"
    )
    unit_id = fields.Many2one(
        'building.floor',
        string="Floor",
        domain="[('id', 'in', available_unit_ids)]"
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        tracking=True
    )
    block_reason = fields.Text(
        string='Block Reason',
        tracking=True
    )
    rejected_by = fields.Many2one(
        'res.users',
        string='Rejected By',
        tracking=True
    )
    rejected_date = fields.Datetime(
        string='Rejected Date',
        tracking=True
    )
    blocked_by = fields.Many2one(
        'res.users',
        string='Blocked By',
        tracking=True
    )
    blocked_date = fields.Datetime(
        string='Blocked Date',
        tracking=True
    )
    unblocked_by = fields.Many2one(
        'res.users',
        string='Unblocked By',
        tracking=True
    )
    unblocked_date = fields.Datetime(
        string='Unblocked Date',
        tracking=True
    )

    # ==================================
    # Action Methods
    # ==================================
    def action_reject(self):
        """Open wizard to enter rejection reason"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rejection Reason'),
            'res_model': 'reject.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model_name': 'access.card',
                'default_record_id': self.id,
            }
        }

    def action_execute_reject(self, reason):
        """Called from wizard to actually reject the record"""
        for rec in self:
            rec.write({
                'state': 'rejected',
                'rejection_reason': reason,
                'rejected_by': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
                'active': False,
            })
            rec.message_post(
                body=_("Request has been rejected. Reason: %(reason)s", reason=reason),
                partner_ids=rec.message_partner_ids.ids,
                message_type='notification'
            )

    def action_block(self):
        """Open wizard to enter block reason"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Block Reason'),
            'res_model': 'block.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model_name': 'access.card',
                'default_record_id': self.id,
            }
        }

    def action_execute_block(self, reason):
        """Called from wizard to actually block the record"""
        for rec in self:
            rec.write({
                'state': 'blocked',
                'block_reason': reason,
                'blocked_by': self.env.user.id,
                'blocked_date': fields.Datetime.now(),
                'active': True,
            })
            rec.message_post(
                body=_("Personal Access has been BLOCKED. Reason: %(reason)s", reason=reason),
                partner_ids=rec.message_partner_ids.ids,
                message_type='notification'
            )

    def action_unblock(self):
        """Restore status to Active"""
        for rec in self:
            # Check unit limit if applicable
            if rec.unit_id and rec.unit_id.access_card_limit:
                active_cards = self.search_count([
                    ('unit_id', '=', rec.unit_id.id),
                    ('state', '=', 'active'),
                    ('id', '!=', rec.id)
                ])
                if active_cards >= rec.unit_id.access_card_limit:
                    raise ValidationError(_(
                        "Cannot unblock this card. The personal card limit for floor %(floor)s has been reached. "
                        "Maximum allowed: %(limit)s cards.",
                        floor=rec.unit_id.name,
                        limit=rec.unit_id.access_card_limit
                    ))

            rec.write({
                'state': 'active',
                'unblocked_by': self.env.user.id,
                'unblocked_date': fields.Datetime.now(),
            })
            rec.message_post(
                body=_("Personal Access has been UNBLOCKED."),
                partner_ids=rec.message_partner_ids.ids,
                message_type='notification'
            )

    def action_activate_selected_personal_card(self):
        """Activate selected parking records"""
        if not self:
            raise ValidationError(_("No records selected."))

        to_activate = self.filtered(lambda r: r.state != 'active')

        if not to_activate:
            raise ValidationError(_("All selected records are already active."))

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
                'message': _('%(count)s record(s) activated successfully.', count=activated_count),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _compute_old_count_access(self):
        for rec in self:
            rec.old_count = self.search_count([
                ('emp_phone', '=', rec.emp_phone),
                ('id', '!=', rec.id)
            ])

    @api.onchange('host_comp_id')
    def action_set_host_company_id(self):
        self.host_company_id = False
        if self.host_comp_id:
            self.host_company_id = self.host_comp_id.partner_id

    @api.depends('host_comp_id', 'host_comp_id.floor_ids')
    def _compute_available_units(self):
        for record in self:
            if record.host_comp_id:
                record.available_unit_ids = record.host_comp_id.floor_ids
            else:
                record.available_unit_ids = False

    def draft_action(self):
        for rec in self:
            rec.active = True
            rec.state = "draft"

    def submit_action(self):
        for rec in self:
            rec.active = True
            rec.state = "management_approval"

    def tech_active_action(self):
        for rec in self:
            rec.active = True
            rec.state = "active"

    def active_action(self):
        for rec in self:
            rec.active = True
            rec.state = "tech_active"

    def disable_action(self):
        for rec in self:
            rec.state = "disable"

    def canceled_action(self):
        for rec in self:
            rec.state = "canceled"

    def action_box_access_card(self):
        self.ensure_one()
        return {
            'name': _("Personal Card History"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'access.card',
            'domain': [('emp_phone', '=', self.emp_phone)],
            'context': {
                'create': False,
                'edit': False,
                'delete': False,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Check card limits before creation"""
        res = super().create(vals_list)
        for rec in res:
            # Check unit limit
            if rec.unit_id and rec.unit_id.access_card_limit:
                active_count = rec.unit_id.access_card_ids.filtered(
                    lambda c: c.state in ['active', 'management_approval', 'tech_active']
                ).count()
                if active_count > rec.unit_id.access_card_limit:
                    raise ValidationError(_(
                        "Personal card limit exceeded for floor %(floor)s. "
                        "Maximum allowed: %(limit)s cards.",
                        floor=rec.unit_id.name,
                        limit=rec.unit_id.access_card_limit
                    ))

            # Check card number uniqueness
            if rec.card_no:
                existing = self.search([('card_no', '=', rec.card_no), ('id', '!=', rec.id)])
                if existing:
                    raise ValidationError(_(
                        "Card number %(card_no)s is already in use!",
                        card_no=rec.card_no
                    ))
        return res

    def write(self, vals):
        """Check limits and constraints during update"""
        for record in self:
            # Check unit limit if changing
            if 'unit_id' in vals or 'state' in vals:
                unit_id = vals.get('unit_id', record.unit_id.id)
                if unit_id:
                    unit = self.env['building.floor'].browse(unit_id)
                    if unit and unit.access_card_limit:
                        active_count = unit.access_card_ids.filtered(
                            lambda c: c.state in ['active', 'management_approval', 'tech_active']
                        ).count()
                        # Add current record if it's active
                        if record.state not in ['canceled', 'rejected'] and (
                                vals.get('state', record.state) not in ['canceled', 'rejected']):
                            active_count += 1
                        if active_count > unit.access_card_limit:
                            raise ValidationError(_(
                                "Personal card limit exceeded for floor %(floor)s. "
                                "Maximum allowed: %(limit)s cards.",
                                floor=unit.name,
                                limit=unit.access_card_limit
                            ))

            # Check card number uniqueness if changing
            if 'card_no' in vals and vals['card_no']:
                existing = self.search([
                    ('card_no', '=', vals['card_no']),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(_(
                        "Card number %(card_no)s is already in use!",
                        card_no=vals['card_no']
                    ))

        return super(AccessCard, self).write(vals)
