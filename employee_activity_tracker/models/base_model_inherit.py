# -*- coding: utf-8 -*-
###############################################################################
# Model: base (inherited)
# Purpose: Global ORM-level tracking engine — automatically tracks create(),
#          write(), unlink() across EVERY model in Odoo without manual setup.
###############################################################################

from odoo import models, fields, api
import logging
import time

_logger = logging.getLogger(__name__)

# Models to NEVER track (system/infrastructure models)
SKIP_TRACKING_MODELS = frozenset([
    'activity.tracker.log',
    'activity.tracker.session',
    'activity.tracker.field.change',
    'activity.tracker.button.click',
    'activity.tracker.security.log',
    'activity.tracker.access.log',
    'activity.tracker.config.model',
    'mail.message',
    'mail.notification',
    'mail.tracking.value',
    'mail.followers',
    'bus.bus',
    'bus.presence',
    'ir.logging',
    'ir.rule',
    'ir.model.access',
    'base.automation',
    'base.automation.line',
    'ir.attachment',          # High volume - track separately if needed
    'ir.ui.view',
    'ir.actions.act_window',
    'ir.actions.server',
    'res.lang',
    'ir.translation',
    'ir.sequence',
    'ir.sequence.date_range',
])


class BaseModelInherit(models.AbstractModel):
    """
    Inherit the base 'base' model to intercept ALL ORM operations.
    This is the global tracking engine — zero configuration required
    for new modules/models.
    """
    _inherit = 'base'

    def _is_tracking_enabled(self):
        """Check if tracking is globally enabled."""
        try:
            param = self.env['ir.config_parameter'].sudo().get_param(
                'activity_tracker.enabled', 'True'
            )
            return param.lower() in ('true', '1', 'yes')
        except Exception:
            return True

    def _should_track_model(self):
        """Check if this model should be tracked."""
        if self._name in SKIP_TRACKING_MODELS:
            return False
        if self._name.startswith('_'):
            return False
        # Check user-configured exclusions
        try:
            excluded_param = self.env['ir.config_parameter'].sudo().get_param(
                'activity_tracker.excluded_models', ''
            )
            excluded = [m.strip() for m in excluded_param.split(',') if m.strip()]
            if self._name in excluded:
                return False
        except Exception:
            pass
        return True

    def _get_module_name(self):
        """Extract the Odoo module name from the model name."""
        module_map = {
            'sale': 'Sales',
            'purchase': 'Purchase',
            'stock': 'Inventory',
            'account': 'Accounting',
            'crm': 'CRM',
            'hr': 'HR/Employees',
            'mrp': 'Manufacturing',
            'project': 'Project',
            'helpdesk': 'Helpdesk',
            'website': 'Website',
            'ecommerce': 'eCommerce',
            'maintenance': 'Maintenance',
            'quality': 'Quality',
            'repair': 'Repair',
            'fleet': 'Fleet',
            'pos': 'Point of Sale',
            'mail': 'Discuss/Mail',
            'calendar': 'Calendar',
            'res': 'Core/Config',
            'ir': 'System',
        }
        prefix = self._name.split('.')[0]
        return module_map.get(prefix, prefix.capitalize())

    def _get_record_display(self, record):
        """Safely get record display name."""
        try:
            return record.display_name or record.name or f"ID:{record.id}"
        except Exception:
            try:
                return f"ID:{record.id}"
            except Exception:
                return 'Unknown'

    # =========================================================================
    # Override create()
    # =========================================================================
    @api.model_create_multi
    def create(self, vals_list):
        """Track record creation across all models."""
        start_time = time.time()
        records = super().create(vals_list)

        if not self._is_tracking_enabled() or not self._should_track_model():
            return records

        try:
            duration_ms = int((time.time() - start_time) * 1000)
            for record in records:
                summary = (
                    f"Created {self._description or self._name}: "
                    f"{self._get_record_display(record)}"
                )
                self.env['activity.tracker.log'].sudo()._log_activity(
                    action_type='create',
                    summary=summary,
                    model_name=self._name,
                    model_description=self._description or self._name,
                    record_id=record.id,
                    record_name=self._get_record_display(record),
                    module_name=self._get_module_name(),
                    result='success',
                    duration_ms=duration_ms,
                )
        except Exception as e:
            _logger.debug("Tracking error on create (%s): %s", self._name, e)

        return records

    # =========================================================================
    # Override write()
    # =========================================================================
    def write(self, vals):
        """Track record updates and field-level changes across all models."""
        if not self._should_track_model() or not vals:
            return super().write(vals)

        # Capture old values BEFORE the write for field change tracking
        track_fields = (
            self._is_tracking_enabled()
            and self.env['ir.config_parameter'].sudo().get_param(
                'activity_tracker.enable_field_tracking', 'True'
            ).lower() in ('true', '1', 'yes')
        )

        old_values = {}
        if track_fields and self:
            try:
                field_names = [k for k in vals.keys() if not k.startswith('_')]
                for fname in field_names:
                    field_def = self._fields.get(fname)
                    if not field_def:
                        continue
                    if fname in ('write_date', 'write_uid', 'create_date', 'create_uid'):
                        continue
                    try:
                        old_values[fname] = {rec.id: rec[fname] for rec in self}
                    except Exception:
                        pass
            except Exception:
                pass

        start_time = time.time()
        result = super().write(vals)
        duration_ms = int((time.time() - start_time) * 1000)

        if not self._is_tracking_enabled() or not self._should_track_model():
            return result

        try:
            for record in self:
                # Log the write activity
                summary = (
                    f"Updated {self._description or self._name}: "
                    f"{self._get_record_display(record)}"
                )
                log_entry = self.env['activity.tracker.log'].sudo()
                log_entry._log_activity(
                    action_type='write',
                    summary=summary,
                    model_name=self._name,
                    model_description=self._description or self._name,
                    record_id=record.id,
                    record_name=self._get_record_display(record),
                    module_name=self._get_module_name(),
                    result='success',
                    duration_ms=duration_ms,
                )

                # Log field-level changes
                if track_fields and old_values:
                    self._log_field_changes_for_record(record, vals, old_values)

        except Exception as e:
            _logger.debug("Tracking error on write (%s): %s", self._name, e)

        return result

    def _log_field_changes_for_record(self, record, vals, old_values):
        """Internal: Log field-level changes for a single record."""
        try:
            batch = []
            ir_model = self.env['ir.model'].sudo().search(
                [('model', '=', self._name)], limit=1
            )
            model_desc = ir_model.name if ir_model else self._name

            for fname, new_val in vals.items():
                field_def = self._fields.get(fname)
                if not field_def:
                    continue
                if fname in ('write_date', 'write_uid', '__last_update'):
                    continue
                old_val_dict = old_values.get(fname, {})
                old_val = old_val_dict.get(record.id)

                old_str = self._tracker_value_to_str(field_def, old_val)
                new_str = self._tracker_value_to_str(field_def, new_val)

                if old_str == new_str:
                    continue

                batch.append({
                    'user_id': self.env.uid,
                    'company_id': self.env.company.id,
                    'model_name': self._name,
                    'model_description': model_desc,
                    'record_id': record.id,
                    'record_name': self._get_record_display(record),
                    'field_name': fname,
                    'field_label': getattr(field_def, 'string', fname),
                    'field_type': field_def.type,
                    'old_value': old_str[:2000],
                    'new_value': new_str[:2000],
                    'change_datetime': fields.Datetime.now(),
                })

            if batch:
                self.env['activity.tracker.field.change'].sudo().create(batch)
        except Exception as e:
            _logger.debug("Field change logging error: %s", e)

    def _tracker_value_to_str(self, field_def, value):
        """Convert field value to human-readable string."""
        if value is None or value is False:
            return ''
        if field_def.type == 'many2one':
            if hasattr(value, 'display_name'):
                return str(value.display_name)
            if hasattr(value, 'id'):
                return f"ID:{value.id}"
            return str(value)
        if field_def.type in ('many2many', 'one2many'):
            if hasattr(value, 'ids'):
                return f"[{', '.join(str(i) for i in value.ids)}]"
            return str(value)
        if field_def.type == 'boolean':
            return 'Yes' if value else 'No'
        return str(value)[:500]

    # =========================================================================
    # Override unlink()
    # =========================================================================
    def unlink(self):
        """Track record deletions across all models."""
        if not self._is_tracking_enabled() or not self._should_track_model():
            return super().unlink()

        # Capture info BEFORE deletion
        deletions = []
        try:
            for record in self:
                deletions.append({
                    'record_id': record.id,
                    'record_name': self._get_record_display(record),
                })
        except Exception:
            pass

        result = super().unlink()

        try:
            for info in deletions:
                summary = (
                    f"Deleted {self._description or self._name}: "
                    f"{info['record_name']}"
                )
                self.env['activity.tracker.log'].sudo()._log_activity(
                    action_type='unlink',
                    summary=summary,
                    model_name=self._name,
                    model_description=self._description or self._name,
                    record_id=info['record_id'],
                    record_name=info['record_name'],
                    module_name=self._get_module_name(),
                    result='success',
                )
        except Exception as e:
            _logger.debug("Tracking error on unlink (%s): %s", self._name, e)

        return result