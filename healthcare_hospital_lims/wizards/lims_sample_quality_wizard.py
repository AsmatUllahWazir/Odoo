# -*- coding: utf-8 -*-
"""
Sample Quality Check Wizard
Allows performing quality checks on samples
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LimsSampleQualityWizard(models.TransientModel):
    """
    Wizard for performing sample quality checks
    """
    _name = 'lims.sample.quality.wizard'
    _description = 'Sample Quality Check Wizard'

    sample_id = fields.Many2one(
        'lims.sample',
        string='Sample',
        required=True
    )

    quality_ok = fields.Boolean(
        string='Quality OK',
        default=True
    )

    hemolysis = fields.Boolean(
        string='Hemolysis Present',
        help='Red blood cell breakdown'
    )

    lipemia = fields.Boolean(
        string='Lipemia Present',
        help='Excess lipids in sample'
    )

    icterus = fields.Boolean(
        string='Icterus Present',
        help='Yellow discoloration due to bilirubin'
    )

    clot_present = fields.Boolean(
        string='Clot Present',
        help='Clot formation in sample'
    )

    insufficient_volume = fields.Boolean(
        string='Insufficient Volume',
        help='Insufficient sample volume'
    )

    contamination = fields.Boolean(
        string='Contamination Detected',
        help='Sample contamination suspected'
    )

    quality_notes = fields.Text(
        string='Quality Notes',
        help='Detailed notes about sample quality'
    )

    @api.constrains('quality_ok', 'quality_notes')
    def _check_quality_notes(self):
        """Ensure notes are provided for failed quality checks"""
        for record in self:
            if not record.quality_ok and not record.quality_notes:
                raise ValidationError(_('Please provide notes for failed quality check!'))

    def action_submit_quality_check(self):
        """Submit the quality check results"""
        self.ensure_one()

        sample = self.sample_id

        # Check if there are any quality issues
        has_issues = any([
            self.hemolysis, self.lipemia, self.icterus,
            self.clot_present, self.insufficient_volume, self.contamination
        ])

        # Determine overall quality
        quality_ok = self.quality_ok and not has_issues

        # Build quality notes
        notes = self.quality_notes or 'Quality check completed'
        if has_issues:
            issues = []
            if self.hemolysis:
                issues.append('Hemolysis')
            if self.lipemia:
                issues.append('Lipemia')
            if self.icterus:
                issues.append('Icterus')
            if self.clot_present:
                issues.append('Clot present')
            if self.insufficient_volume:
                issues.append('Insufficient volume')
            if self.contamination:
                issues.append('Contamination')
            notes = f"Quality issues detected: {', '.join(issues)}. " + notes

        # Update sample
        sample.write({
            'quality_ok': quality_ok,
            'hemolysis': self.hemolysis,
            'lipemia': self.lipemia,
            'icterus': self.icterus,
            'clot_present': self.clot_present,
            'quality_notes': notes,
        })

        # If quality is not OK, reject the sample
        if not quality_ok:
            sample.status = 'rejected'
            sample.message_post(
                body=_('Sample rejected due to quality issues: %s') % notes,
                message_type='notification'
            )
        else:
            sample.message_post(
                body=_('Quality check passed: %s') % notes,
                message_type='notification'
            )

        return {'type': 'ir.actions.act_window_close'}
    