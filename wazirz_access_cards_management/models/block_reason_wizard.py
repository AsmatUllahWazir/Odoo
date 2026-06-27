from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class BlockReasonWizard(models.TransientModel):
    _name = 'block.reason.wizard'
    _description = 'Block Reason Wizard'

    reason = fields.Text(
        string='Block Reason',
        required=True,
        help='Please provide a detailed reason for blocking this card'
    )
    model_name = fields.Char(
        string='Model Name',
        required=True,
        help='Technical name of the model to block'
    )
    record_id = fields.Integer(
        string='Record ID',
        required=True,
        help='ID of the record to block'
    )

    @api.constrains('model_name')
    def _check_model_name(self):
        for wizard in self:
            if wizard.model_name:
                model = self.env.get(wizard.model_name)
                if not model:
                    raise ValidationError(_("Model '%s' does not exist!") % wizard.model_name)

    @api.constrains('record_id', 'model_name')
    def _check_record_exists(self):
        for wizard in self:
            if wizard.model_name and wizard.record_id:
                model = self.env[wizard.model_name]
                record = model.browse(wizard.record_id)
                if not record.exists():
                    raise ValidationError(_("The target record no longer exists!"))

    def action_confirm(self):
        """Apply block to the target record"""
        self.ensure_one()

        if not self.model_name:
            raise UserError(_("No model specified!"))

        if not self.record_id:
            raise UserError(_("No record specified!"))

        # Get the model and record
        model = self.env[self.model_name]
        record = model.browse(self.record_id)

        if not record.exists():
            raise UserError(_("The record no longer exists!"))

        # Check if record has the block method
        if not hasattr(record, 'action_execute_block'):
            raise UserError(_("This record type does not support blocking!"))

        # Check if card is already blocked
        if record.state == 'blocked':
            raise UserError(_("This card is already blocked!"))

        # Execute the block
        try:
            record.action_execute_block(self.reason)
        except Exception as e:
            raise UserError(_("Failed to block: %s") % str(e))

        # Close the wizard
        return {'type': 'ir.actions.act_window_close'}
    