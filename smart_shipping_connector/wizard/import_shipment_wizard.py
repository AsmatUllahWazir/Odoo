from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
import base64
import csv
import io
from datetime import datetime

_logger = logging.getLogger(__name__)


class ImportShipmentWizard(models.TransientModel):
    _name = 'shipping.import.shipment.wizard'
    _description = 'Import Shipment Wizard'

    file_data = fields.Binary(
        string='File',
        required=True,
        help='CSV file with shipment data'
    )
    file_name = fields.Char(string='File Name')
    file_type = fields.Selection([
        ('csv', 'CSV'),
        ('xlsx', 'Excel'),
    ], string='File Type', default='csv', required=True)

    import_type = fields.Selection([
        ('new', 'Create New Shipments'),
        ('update', 'Update Existing Shipments'),
    ], string='Import Type', default='new', required=True)

    dry_run = fields.Boolean(
        string='Dry Run',
        default=True,
        help='Validate without creating/updating'
    )

    preview_data = fields.Text(string='Preview Data', readonly=True)

    def action_preview(self):
        """Preview imported data"""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_('Please upload a file.'))

        data = base64.b64decode(self.file_data)
        if self.file_type == 'csv':
            preview = self._parse_csv(data)
        else:
            preview = self._parse_excel(data)

        self.preview_data = str(preview[:5])  # Show first 5 rows

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Preview Ready'),
                'message': _('Data preview generated. Review the data before importing.'),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_import(self):
        """Import shipments"""
        self.ensure_one()
        if not self.file_data:
            raise UserError(_('Please upload a file.'))

        data = base64.b64decode(self.file_data)
        if self.file_type == 'csv':
            rows = self._parse_csv(data)
        else:
            rows = self._parse_excel(data)

        if not rows:
            raise UserError(_('No data found in file.'))

        if self.dry_run:
            return self._validate_data(rows)

        return self._import_data(rows)

    def _parse_csv(self, data):
        """Parse CSV data"""
        try:
            text = data.decode('utf-8')
            reader = csv.DictReader(io.StringIO(text))
            return [row for row in reader]
        except Exception as e:
            raise UserError(_('Failed to parse CSV: %s') % str(e))

    def _parse_excel(self, data):
        """Parse Excel data"""
        try:
            import openpyxl
            workbook = openpyxl.load_workbook(io.BytesIO(data))
            sheet = workbook.active

            headers = [cell.value for cell in sheet[1]]
            rows = []
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if any(row):
                    rows.append(dict(zip(headers, row)))
            return rows
        except Exception as e:
            raise UserError(_('Failed to parse Excel: %s') % str(e))

    def _validate_data(self, rows):
        """Validate imported data"""
        errors = []
        valid_count = 0

        for i, row in enumerate(rows, start=2):
            try:
                self._validate_row(row)
                valid_count += 1
            except ValidationError as e:
                errors.append(f"Row {i}: {str(e)}")

        message = f"Validated {len(rows)} rows, {valid_count} valid, {len(errors)} errors"
        if errors:
            message += f"\nErrors:\n{chr(10).join(errors[:10])}"
            if len(errors) > 10:
                message += f"\n... and {len(errors) - 10} more errors"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Validation Complete'),
                'message': message,
                'type': 'warning' if errors else 'success',
                'sticky': True,
            }
        }

    def _validate_row(self, row):
        """Validate a single row"""
        required_fields = ['recipient_name', 'recipient_address']
        for field in required_fields:
            if not row.get(field):
                raise ValidationError(_('Missing required field: %s') % field)

    def _import_data(self, rows):
        """Import shipments"""
        created = 0
        updated = 0
        errors = []

        for i, row in enumerate(rows, start=2):
            try:
                shipment = self._create_or_update_shipment(row)
                if shipment:
                    if self.import_type == 'new':
                        created += 1
                    else:
                        updated += 1
            except Exception as e:
                errors.append(f"Row {i}: {str(e)}")

        message = f"Imported {created} new, updated {updated} shipments"
        if errors:
            message += f"\nErrors:\n{chr(10).join(errors[:10])}"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Complete'),
                'message': message,
                'type': 'success' if not errors else 'warning',
                'sticky': True,
            }
        }

    def _create_or_update_shipment(self, row):
        """Create or update shipment from row data"""
        Shipment = self.env['shipping.shipment']

        vals = {
            'recipient_name': row.get('recipient_name'),
            'recipient_address': row.get('recipient_address'),
            'recipient_phone': row.get('recipient_phone', ''),
            'recipient_email': row.get('recipient_email', ''),
            'total_weight': float(row.get('total_weight', 1.0)),
            'declared_value': float(row.get('declared_value', 0.0)),
        }

        if row.get('carrier_code'):
            carrier = self.env['shipping.carrier.provider'].search([
                ('code', '=', row.get('carrier_code'))
            ], limit=1)
            if carrier:
                vals['carrier_provider_id'] = carrier.id
                account = carrier.account_ids[:1]
                if account:
                    vals['carrier_account_id'] = account.id

        if self.import_type == 'new':
            return Shipment.create(vals)
        else:
            existing = Shipment.search([
                ('name', '=', row.get('shipment_reference'))
            ], limit=1)
            if existing:
                existing.write(vals)
                return existing
            return Shipment.create(vals)
        