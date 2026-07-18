# -*- coding: utf-8 -*-
"""
Interpretation Wizard
Adds clinical interpretation to test results
"""
from odoo import api, fields, models, _


class LimsInterpretationWizard(models.TransientModel):
    """
    Wizard for adding interpretation to a test line
    """
    _name = 'lims.interpretation.wizard'
    _description = 'Interpretation Wizard'

    test_line_id = fields.Many2one(
        'lims.test_order_line',
        string='Test Line',
        required=True
    )

    interpretation = fields.Text(
        string='Interpretation',
        required=True,
        help='Clinical interpretation of the results'
    )

    template_id = fields.Many2one(
        'lims.result_template',
        string='Template',
        help='Use a template for interpretation'
    )

    use_auto_generation = fields.Boolean(
        string='Auto-generate from Template',
        default=False,
        help='Automatically generate interpretation based on result template'
    )

    @api.onchange('template_id', 'test_line_id')
    def _onchange_template_id(self):
        """Load template interpretation"""
        if self.template_id and self.test_line_id:
            result_value = self.test_line_id.result_value
            patient_age = self.test_line_id.patient_age
            patient_gender = self.test_line_id.patient_id.gender

            interpretation = self.template_id.get_interpretation(
                result_value, patient_age, patient_gender
            )
            if interpretation:
                self.interpretation = interpretation

    @api.onchange('use_auto_generation')
    def _onchange_use_auto_generation(self):
        """Auto-generate interpretation"""
        if self.use_auto_generation and self.test_line_id:
            template = self.env['lims.result_template'].search([
                ('test_type_id', '=', self.test_line_id.test_type_id.id),
                ('is_default', '=', True)
            ], limit=1)

            if template:
                self.template_id = template.id

    def action_save_interpretation(self):
        """Save the interpretation"""
        self.ensure_one()

        self.test_line_id.write({
            'interpretation': self.interpretation
        })

        self.test_line_id.message_post(
            body=_('Interpretation added: %s') % self.interpretation,
            message_type='notification'
        )

        return {'type': 'ir.actions.act_window_close'}
    