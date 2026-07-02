# -*- coding: utf-8 -*-
###############################################################################
# Model: activity.tracker.field.change
# Purpose: Track old → new values for every field change across all models
###############################################################################

from odoo import models, fields, api
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class ActivityTrackerFieldChange(models.Model):
    """
    Detailed field-level change tracking.
    For every write() on any model, records each changed field with
    old value, new value, user, timestamp, model, and record.
    """
    _name = 'activity.tracker.field.change'
    _description = 'Field Change Log'
    _order = 'change_datetime desc'
    _log_access = False

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------
    user_id = fields.Many2one(
        'res.users', string='User', required=True,
        ondelete='restrict', index=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company', index=True
    )
    activity_log_id = fields.Many2one(
        'activity.tracker.log', string='Activity Log',
        ondelete='cascade'
    )

    # -------------------------------------------------------------------------
    # Target Resource
    # -------------------------------------------------------------------------
    model_name = fields.Char(
        string='Model', required=True, index=True
    )
    model_description = fields.Char(
        string='Object Name'
    )
    record_id = fields.Integer(
        string='Record ID', required=True, index=True
    )
    record_name = fields.Char(
        string='Record Name'
    )

    # -------------------------------------------------------------------------
    # Field Details
    # -------------------------------------------------------------------------
    field_name = fields.Char(
        string='Field (Technical)', required=True, index=True
    )
    field_label = fields.Char(
        string='Field Label'
    )
    field_type = fields.Char(
        string='Field Type'
    )

    # -------------------------------------------------------------------------
    # Values
    # -------------------------------------------------------------------------
    old_value = fields.Text(string='Old Value')
    new_value = fields.Text(string='New Value')
    old_value_display = fields.Char(
        string='Old Value (Display)', compute='_compute_display_values'
    )
    new_value_display = fields.Char(
        string='New Value (Display)', compute='_compute_display_values'
    )

    # -------------------------------------------------------------------------
    # Timestamp
    # -------------------------------------------------------------------------
    change_datetime = fields.Datetime(
        string='Changed At', required=True,
        default=fields.Datetime.now, index=True
    )

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------
    change_summary = fields.Char(
        string='Summary', compute='_compute_summary'
    )

    @api.depends('old_value', 'new_value')
    def _compute_display_values(self):
        for rec in self:
            rec.old_value_display = (rec.old_value or '')[:100]
            rec.new_value_display = (rec.new_value or '')[:100]

    @api.depends('field_label', 'model_description', 'record_name')
    def _compute_summary(self):
        for rec in self:
            field = rec.field_label or rec.field_name or 'Unknown Field'
            record = rec.record_name or f"ID:{rec.record_id}"
            model = rec.model_description or rec.model_name or ''
            rec.change_summary = f"{model} / {record} → {field}"

    # -------------------------------------------------------------------------
    # Helper: Batch log field changes
    # -------------------------------------------------------------------------
    @api.model
    def _log_field_changes(self, model_obj, record, values, activity_log_id=None):
        """
        Called after a write() to record field-level changes.

        :param model_obj: The Odoo model instance (e.g., self.env['sale.order'])
        :param record: The recordset that was written
        :param values: Dict of values that were written
        :param activity_log_id: Related activity log ID
        """
        try:
            # Models to skip (performance-critical or already tracked)
            skip_models = {
                'activity.tracker.log',
                'activity.tracker.session',
                'activity.tracker.field.change',
                'activity.tracker.button.click',
                'activity.tracker.security.log',
                'activity.tracker.access.log',
                'mail.message',
                'mail.tracking.value',
                'bus.bus',
                'ir.logging',
            }
            model_name = model_obj._name
            if model_name in skip_models:
                return

            # Get field metadata
            ir_model = self.env['ir.model'].sudo().search(
                [('model', '=', model_name)], limit=1
            )
            model_desc = ir_model.name if ir_model else model_name

            # Skip if no important fields changed
            tracked_field_types = {
                'char', 'text', 'integer', 'float', 'monetary',
                'boolean', 'date', 'datetime', 'selection',
                'many2one', 'many2many', 'one2many',
            }

            batch = []
            for rec in record:
                for fname, new_val in values.items():
                    field_def = model_obj._fields.get(fname)
                    if not field_def:
                        continue
                    if field_def.type not in tracked_field_types:
                        continue
                    # Skip internal/system fields
                    if fname.startswith('_') or fname in (
                        'write_date', 'write_uid', 'create_date', 'create_uid',
                        '__last_update',
                    ):
                        continue

                    try:
                        old_val = rec[fname]
                    except Exception:
                        old_val = None

                    # Resolve display values
                    old_str = self._value_to_str(field_def, old_val)
                    new_str = self._value_to_str(field_def, new_val)

                    if old_str == new_str:
                        continue  # No actual change

                    # Get field label
                    field_label = field_def.string if hasattr(field_def, 'string') else fname

                    batch.append({
                        'user_id': self.env.uid,
                        'company_id': self.env.company.id,
                        'activity_log_id': activity_log_id,
                        'model_name': model_name,
                        'model_description': model_desc,
                        'record_id': rec.id,
                        'record_name': self._get_record_name(rec),
                        'field_name': fname,
                        'field_label': field_label,
                        'field_type': field_def.type,
                        'old_value': old_str,
                        'new_value': new_str,
                        'change_datetime': fields.Datetime.now(),
                    })

            if batch:
                self.sudo().create(batch)
        except Exception as e:
            _logger.debug("Field change logging failed: %s", str(e))

    def _value_to_str(self, field_def, value):
        """Convert a field value to a string for storage."""
        if value is None or value is False:
            return ''
        if field_def.type == 'many2one':
            if hasattr(value, 'name'):
                return str(value.name)
            return str(value)
        if field_def.type in ('many2many', 'one2many'):
            if hasattr(value, 'mapped'):
                return ', '.join(value.mapped('name') or [str(v) for v in value.ids])
            return str(value)
        return str(value)

    def _get_record_name(self, record):
        """Safely get the display name of a record."""
        try:
            return record.display_name or record.name or f"ID:{record.id}"
        except Exception:
            return f"ID:{record.id}"

    def unlink(self):
        if not self.env.user.has_group('employee_activity_tracker.group_tracker_admin'):
            raise AccessError("You are not allowed to delete field change logs.")
        return super().unlink()