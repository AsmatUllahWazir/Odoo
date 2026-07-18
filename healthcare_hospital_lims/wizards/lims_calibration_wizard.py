# -*- coding: utf-8 -*-
"""
Calibration Wizard
Records instrument calibration details
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LimsCalibrationWizard(models.TransientModel):
    """
    Wizard for recording instrument calibration
    """
    _name = 'lims.calibration.wizard'
    _description = 'Calibration Wizard'

    instrument_id = fields.Many2one(
        'lims.instrument',
        string='Instrument',
        required=True
    )

    calibration_date = fields.Date(
        string='Calibration Date',
        required=True,
        default=fields.Date.today
    )

    calibration_provider = fields.Char(
        string='Calibration Provider',
        required=True
    )

    calibration_certificate = fields.Binary(
        string='Calibration Certificate'
    )

    certificate_filename = fields.Char(
        string='Certificate Filename'
    )

    next_calibration_date = fields.Date(
        string='Next Calibration Date',
        help='If not set, will be calculated based on frequency'
    )

    notes = fields.Text(
        string='Notes',
        help='Additional notes about calibration'
    )

    @api.onchange('instrument_id')
    def _onchange_instrument_id(self):
        """Set next calibration date"""
        if self.instrument_id:
            from datetime import timedelta
            frequency = self.instrument_id.calibration_frequency or 180
            self.next_calibration_date = self.calibration_date + timedelta(days=frequency)

    @api.constrains('calibration_date', 'next_calibration_date')
    def _check_dates(self):
        """Validate calibration dates"""
        for record in self:
            if record.next_calibration_date and record.next_calibration_date <= record.calibration_date:
                raise ValidationError(_('Next calibration date must be after calibration date!'))

    def action_record_calibration(self):
        """Record the calibration"""
        self.ensure_one()

        self.instrument_id.write({
            'calibration_date': self.calibration_date,
            'calibration_provider': self.calibration_provider,
            'calibration_certificate': self.calibration_certificate,
            'certificate_filename': self.certificate_filename,
            'status': 'active',
        })

        # Update next calibration date if provided
        if self.next_calibration_date:
            # Calculate new frequency based on dates
            delta = (self.next_calibration_date - self.calibration_date).days
            if delta > 0:
                self.instrument_id.write({
                    'calibration_frequency': delta
                })

        self.instrument_id.message_post(
            body=_('Calibration recorded. Provider: %s') % self.calibration_provider,
            message_type='notification'
        )

        return {'type': 'ir.actions.act_window_close'}
    