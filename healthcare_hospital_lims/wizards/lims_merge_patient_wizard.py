# -*- coding: utf-8 -*-
"""
Patient Merge Wizard
Allows merging duplicate patient records
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class LimsPatientMergeWizard(models.TransientModel):
    """
    Wizard for merging duplicate patient records
    """
    _name = 'lims.patient.merge.wizard'
    _description = 'Patient Merge Wizard'

    primary_patient_id = fields.Many2one(
        'lims.patient',
        string='Primary Patient',
        required=True,
        help='The patient record that will remain after merging'
    )

    secondary_patient_ids = fields.Many2many(
        'lims.patient',
        string='Patients to Merge',
        help='Patient records to merge into the primary'
    )

    merge_orders = fields.Boolean(
        string='Merge Test Orders',
        default=True
    )

    merge_samples = fields.Boolean(
        string='Merge Samples',
        default=True
    )

    merge_reports = fields.Boolean(
        string='Merge Reports',
        default=True
    )

    merge_medical_history = fields.Boolean(
        string='Merge Medical History',
        default=True
    )

    delete_after_merge = fields.Boolean(
        string='Delete Secondary Records',
        default=False,
        help='Permanently delete secondary patient records after merge'
    )

    @api.constrains('primary_patient_id', 'secondary_patient_ids')
    def _check_patients(self):
        """Validate patients for merging"""
        for record in self:
            if record.primary_patient_id in record.secondary_patient_ids:
                raise ValidationError(_('Primary patient cannot be in secondary patients list!'))
            if len(record.secondary_patient_ids) < 1:
                raise ValidationError(_('Please select at least one patient to merge!'))

    def action_merge(self):
        """Execute the merge operation"""
        self.ensure_one()
        primary = self.primary_patient_id
        secondary = self.secondary_patient_ids

        if not secondary:
            raise UserError(_('No secondary patients selected for merging!'))

        merged_count = 0
        errors = []

        for patient in secondary:
            try:
                self._merge_single_patient(primary, patient)
                merged_count += 1

                if self.delete_after_merge:
                    patient.unlink()
                else:
                    patient.write({'active': False})

            except Exception as e:
                errors.append(f"Error merging {patient.name}: {str(e)}")

        primary.message_post(
            body=_('Merged patients: %s') % ', '.join(secondary.mapped('display_name')),
            message_type='notification'
        )

        if errors:
            raise UserError(_('Merge completed with errors:\n%s') % '\n'.join(errors))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lims.patient',
            'res_id': primary.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _merge_single_patient(self, primary, secondary):
        """Merge a single patient into primary"""
        # Merge test orders
        if self.merge_orders:
            orders = self.env['lims.test_order'].search([('patient_id', '=', secondary.id)])
            if orders:
                orders.write({'patient_id': primary.id})
                primary.message_post(
                    body=_('Merged %d test orders from %s') % (len(orders), secondary.display_name)
                )

        # Merge samples
        if self.merge_samples:
            samples = self.env['lims.sample'].search([('patient_id', '=', secondary.id)])
            if samples:
                samples.write({'patient_id': primary.id})
                primary.message_post(
                    body=_('Merged %d samples from %s') % (len(samples), secondary.display_name)
                )

        # Merge reports
        if self.merge_reports:
            reports = self.env['lims.report'].search([('patient_id', '=', secondary.id)])
            if reports:
                reports.write({'patient_id': primary.id})
                primary.message_post(
                    body=_('Merged %d reports from %s') % (len(reports), secondary.display_name)
                )

        # Merge medical history
        if self.merge_medical_history and secondary.medical_history:
            primary_hist = primary.medical_history or ''
            secondary_hist = secondary.medical_history or ''
            primary.write({
                'medical_history': f"{primary_hist}\n\n--- Merged from {secondary.display_name} ---\n{secondary_hist}"
            })

        # Merge allergies
        if self.merge_medical_history and secondary.allergies:
            primary_allergies = primary.allergies or ''
            secondary_allergies = secondary.allergies or ''
            if secondary_allergies and primary_allergies:
                primary.write({
                    'allergies': f"{primary_allergies}\n{secondary_allergies}"
                })
            elif secondary_allergies:
                primary.write({
                    'allergies': secondary_allergies
                })

        # Merge medications
        if self.merge_medical_history and secondary.current_medications:
            primary_meds = primary.current_medications or ''
            secondary_meds = secondary.current_medications or ''
            if secondary_meds and primary_meds:
                primary.write({
                    'current_medications': f"{primary_meds}\n{secondary_meds}"
                })
            elif secondary_meds:
                primary.write({
                    'current_medications': secondary_meds
                })
                