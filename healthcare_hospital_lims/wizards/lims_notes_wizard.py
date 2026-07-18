# -*- coding: utf-8 -*-
"""
Notes Wizard
Adds notes to test results
"""
from odoo import api, fields, models, _


class LimsNotesWizard(models.TransientModel):
    """
    Wizard for adding notes to a test line
    """
    _name = 'lims.notes.wizard'
    _description = 'Notes Wizard'

    test_line_id = fields.Many2one(
        'lims.test_order_line',
        string='Test Line',
        required=True
    )

    notes = fields.Text(
        string='Notes',
        required=True,
        help='Additional notes about the test'
    )

    def action_save_notes(self):
        """Save the notes"""
        self.ensure_one()

        self.test_line_id.write({
            'notes': self.notes
        })

        self.test_line_id.message_post(
            body=_('Notes added: %s') % self.notes,
            message_type='notification'
        )

        return {'type': 'ir.actions.act_window_close'}
    