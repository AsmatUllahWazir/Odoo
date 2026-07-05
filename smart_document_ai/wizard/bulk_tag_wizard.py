# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BulkTagWizard(models.TransientModel):
    _name = 'bulk.tag.wizard'
    _description = 'Bulk Tag Wizard'

    document_ids = fields.Many2many(
        'smart.document',
        'bulk_tag_wizard_doc_rel',
        'wizard_id',
        'document_id',
        string='Documents',
    )
    tag_ids = fields.Many2many(
        'document.tag',
        string='Tags to Add',
    )
    remove_existing = fields.Boolean(
        string='Remove Existing Tags',
        default=False,
    )
    action = fields.Selection([
        ('add', 'Add Tags'),
        ('remove', 'Remove Tags'),
    ], string='Action', default='add', required=True)

    def action_apply(self):
        self.ensure_one()
        if not self.document_ids:
            return {'type': 'ir.actions.act_window_close'}

        if not self.tag_ids:
            return {'type': 'ir.actions.act_window_close'}

        if self.action == 'add':
            if self.remove_existing:
                self.document_ids.write({
                    'tag_ids': [(6, 0, self.tag_ids.ids)]
                })
            else:
                for doc in self.document_ids:
                    doc.tag_ids = [(4, tag.id) for tag in self.tag_ids if tag.id not in doc.tag_ids.ids]
        else:
            for doc in self.document_ids:
                doc.tag_ids = [(3, tag.id) for tag in self.tag_ids if tag.id in doc.tag_ids.ids]

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
