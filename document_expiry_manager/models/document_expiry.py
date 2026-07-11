# -*- coding: utf-8 -*-
import logging
from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class DocumentExpiry(models.Model):
    _name = 'document.expiry'
    _description = 'Tracked Document / License'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'
    _rec_name = 'name'

    name = fields.Char(required=True, tracking=True, help="Descriptive title of the document.")
    reference = fields.Char(string='Document Number', help="e.g. license/policy/contract number.")
    document_type_id = fields.Many2one(
        'document.expiry.type', string='Document Type', required=True, tracking=True,
        ondelete='restrict')

    # Generic link to ANY record in the database
    related_model_id = fields.Many2one(
        'ir.model', string='Applies To', required=True, ondelete='restrict',
        domain=[('transient', '=', False)],
        help="The type of record this document is attached to (e.g. Contact, Employee, Vehicle).")
    related_model_name = fields.Char(related='related_model_id.model', store=True, readonly=True)
    related_record_id = fields.Integer(
        string='Record ID', required=True,
        help="Internal database ID of the related record.")
    related_record_name = fields.Char(
        string='Related Record', compute='_compute_related_record_name', store=True)

    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(required=True, tracking=True)
    days_remaining = fields.Integer(
        string='Days Remaining', compute='_compute_days_remaining', store=True,
        help="Negative values mean the document has already expired.")

    warning_days = fields.Integer(
        string='Warning Window (days)', default=30,
        help="Days before expiry at which this document is flagged 'Expiring Soon'.")
    reminder_schedule = fields.Char(
        string='Reminder Schedule (days)', default='30,15,7,1',
        help="Comma separated day thresholds before expiry at which a reminder is created.")
    reminders_sent = fields.Char(default='', readonly=True, copy=False)

    state = fields.Selection([
        ('valid', 'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('renewed', 'Renewed'),
        ('cancelled', 'Cancelled'),
    ], default='valid', required=True, tracking=True, copy=False)

    responsible_id = fields.Many2one(
        'res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    notes = fields.Text()
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')

    @api.depends('related_model_id', 'related_record_id')
    def _compute_related_record_name(self):
        for rec in self:
            name = False
            if rec.related_model_id and rec.related_record_id:
                model = rec.related_model_id.model
                try:
                    if model in self.env:
                        target = self.env[model].sudo().browse(rec.related_record_id)
                        if target.exists():
                            name = target.display_name
                        else:
                            name = _('Record not found (ID %s)') % rec.related_record_id
                except Exception:  # noqa: BLE001 - defensive, model may not support display_name
                    _logger.warning("Could not resolve display name for %s,%s", model, rec.related_record_id)
                    name = _('ID %s') % rec.related_record_id
            rec.related_record_name = name

    @api.depends('expiry_date')
    def _compute_days_remaining(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.expiry_date:
                rec.days_remaining = (rec.expiry_date - today).days
            else:
                rec.days_remaining = 0

    @api.constrains('related_model_id', 'related_record_id')
    def _check_related_record_exists(self):
        for rec in self:
            if rec.related_model_id and rec.related_record_id:
                model = rec.related_model_id.model
                if model not in self.env:
                    raise ValidationError(_("Unknown model '%s'.") % model)
                if not self.env[model].sudo().browse(rec.related_record_id).exists():
                    raise ValidationError(
                        _("The related record (ID %s) does not exist for model '%s'.")
                        % (rec.related_record_id, model))

    @api.constrains('reminder_schedule')
    def _check_reminder_schedule(self):
        for rec in self:
            for token in rec._get_reminder_thresholds():
                if token < 0:
                    raise ValidationError(_("Reminder day thresholds must be positive integers."))

    def _get_reminder_thresholds(self):
        self.ensure_one()
        thresholds = []
        for token in (self.reminder_schedule or '').split(','):
            token = token.strip()
            if not token:
                continue
            try:
                thresholds.append(int(token))
            except ValueError:
                raise ValidationError(
                    _("Invalid reminder schedule '%s'. Use comma separated numbers, e.g. 30,15,7,1")
                    % self.reminder_schedule)
        return sorted(set(thresholds), reverse=True)

    @api.onchange('document_type_id')
    def _onchange_document_type_id(self):
        if self.document_type_id:
            self.warning_days = self.document_type_id.default_warning_days or self.warning_days
            self.reminder_schedule = self.document_type_id.default_reminder_schedule or self.reminder_schedule

    def open_related_record(self):
        self.ensure_one()
        if not self.related_model_id or not self.env[self.related_model_id.model].sudo().browse(
                self.related_record_id).exists():
            raise UserError(_("The related record could not be found."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.related_model_id.model,
            'res_id': self.related_record_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_renew_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renew Document'),
            'res_model': 'document.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_id': self.id,
                'default_new_issue_date': fields.Date.context_today(self),
            },
        }

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            rec.message_post(body=_("Document marked as Cancelled."))

    def action_reset_to_valid(self):
        for rec in self:
            rec.write({'state': 'valid', 'reminders_sent': ''})
            rec.message_post(body=_("Document reset to Valid."))

    def _notify_stage(self, body, activity_summary):
        """Post a chatter message and schedule/refresh an activity for the responsible user."""
        self.ensure_one()
        self.message_post(body=body)
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        existing = self.activity_ids.filtered(
            lambda a: a.user_id == self.responsible_id and a.summary == activity_summary)
        if not existing and self.responsible_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo' if activity_type else False,
                summary=activity_summary,
                note=body,
                user_id=self.responsible_id.id,
                date_deadline=fields.Date.context_today(self),
            )

    @api.model
    def _cron_check_expiry(self):
        """Scheduled action: recompute status and fire reminders for active documents."""
        today = date.today()
        documents = self.search([
            ('active', '=', True),
            ('state', 'not in', ['renewed', 'cancelled']),
        ])
        for rec in documents:
            if not rec.expiry_date:
                continue
            days = (rec.expiry_date - today).days
            sent = [t.strip() for t in (rec.reminders_sent or '').split(',') if t.strip()]

            if days < 0:
                if rec.state != 'expired':
                    rec.state = 'expired'
                    rec._notify_stage(
                        body=_("<b>%s</b> has EXPIRED on %s.") % (rec.name, rec.expiry_date),
                        activity_summary=_("Document expired: %s") % rec.name,
                    )
                continue

            new_state = 'expiring' if days <= (rec.warning_days or 0) else 'valid'
            if new_state != rec.state:
                rec.state = new_state

            for threshold in rec._get_reminder_thresholds():
                if days <= threshold and str(threshold) not in sent:
                    rec._notify_stage(
                        body=_("<b>%s</b> will expire in %s day(s) (on %s).")
                        % (rec.name, days, rec.expiry_date),
                        activity_summary=_("Document expiring soon: %s") % rec.name,
                    )
                    sent.append(str(threshold))
                    rec.reminders_sent = ','.join(sent)
