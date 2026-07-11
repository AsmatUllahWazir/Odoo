# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DocumentExpiryType(models.Model):
    _name = 'document.expiry.type'
    _description = 'Document Expiry Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(help="Optional short code, e.g. 'PASSPORT', 'INSUR'.")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    default_warning_days = fields.Integer(
        string='Default Warning Window (days)', default=30,
        help="Number of days before the expiry date at which a document of this "
             "type is automatically flagged as 'Expiring Soon'.")
    default_reminder_schedule = fields.Char(
        string='Default Reminder Schedule', default='30,15,7,1',
        help="Comma separated list of day thresholds (before expiry) at which a "
             "reminder notification/activity should automatically be created. "
             "e.g. '30,15,7,1' will remind 30, 15, 7 and 1 day(s) before expiry.")
    document_count = fields.Integer(compute='_compute_document_count')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)',
         'A document expiry type with this name already exists for this company.'),
    ]

    def _compute_document_count(self):
        grouped = self.env['document.expiry']._read_group(
            [('document_type_id', 'in', self.ids)],
            ['document_type_id'], ['__count'],
        )
        counts = {dt.id: count for dt, count in grouped}
        for rec in self:
            rec.document_count = counts.get(rec.id, 0)

    def action_view_documents(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'document_expiry_manager.action_document_expiry')
        action['domain'] = [('document_type_id', '=', self.id)]
        action['context'] = {'default_document_type_id': self.id}
        return action
