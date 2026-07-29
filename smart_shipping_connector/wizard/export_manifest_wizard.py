from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
import base64
from io import BytesIO
from datetime import datetime

_logger = logging.getLogger(__name__)


class ExportManifestWizard(models.TransientModel):
    _name = 'shipping.export.manifest.wizard'
    _description = 'Export Manifest Wizard'

    shipment_ids = fields.Many2many(
        'shipping.shipment',
        string='Shipments',
        required=True,
        help='Select shipments to export'
    )

    manifest_type = fields.Selection([
        ('carrier', 'Carrier Manifest'),
        ('customs', 'Customs Manifest'),
        ('internal', 'Internal Manifest'),
        ('summary', 'Summary Manifest'),
    ], string='Manifest Type', default='carrier', required=True)

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    include_details = fields.Boolean(string='Include Package Details', default=True)
    include_cost = fields.Boolean(string='Include Cost Information', default=True)
    include_tracking = fields.Boolean(string='Include Tracking', default=True)

    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
        ('xlsx', 'Excel'),
    ], string='Output Format', default='pdf', required=True)

    def action_generate_manifest(self):
        """Generate manifest"""
        self.ensure_one()

        if not self.shipment_ids:
            raise UserError(_('Please select at least one shipment.'))

        manifest_data = self._generate_manifest_data()

        if self.output_format == 'pdf':
            return self._generate_pdf(manifest_data)
        elif self.output_format == 'csv':
            return self._generate_csv(manifest_data)
        else:
            return self._generate_excel(manifest_data)

    def _generate_manifest_data(self):
        """Generate manifest data"""
        data = {
            'manifest_type': self.manifest_type,
            'generated_date': datetime.now(),
            'shipments': [],
            'totals': {
                'total_shipments': 0,
                'total_weight': 0.0,
                'total_cost': 0.0,
                'total_packages': 0,
            }
        }

        for shipment in self.shipment_ids:
            shipment_data = {
                'reference': shipment.name,
                'carrier': shipment.carrier_provider_id.name,
                'service': shipment.service_type or 'Standard',
                'tracking': shipment.tracking_number or 'N/A',
                'recipient': shipment.recipient_name,
                'recipient_address': shipment.recipient_address,
                'weight': shipment.total_weight,
                'packages': shipment.total_packages,
                'cost': shipment.shipping_cost,
                'state': shipment.get_tracking_status_display(),
                'date_created': shipment.create_date,
                'date_delivered': shipment.delivered_date,
                'is_international': shipment.is_international,
                'package_details': [],
            }

            # Package details
            if self.include_details:
                for package in shipment.package_ids:
                    shipment_data['package_details'].append({
                        'name': package.name,
                        'type': package.package_type,
                        'weight': package.weight,
                        'dimensions': f"{package.length}x{package.width}x{package.height}",
                        'tracking': package.tracking_number or 'N/A',
                    })

            data['shipments'].append(shipment_data)

            # Update totals
            data['totals']['total_shipments'] += 1
            data['totals']['total_weight'] += shipment.total_weight or 0
            data['totals']['total_cost'] += shipment.shipping_cost or 0
            data['totals']['total_packages'] += shipment.total_packages or 0

        return data

    def _generate_pdf(self, manifest_data):
        """Generate PDF manifest"""
        # TODO: Implement PDF generation with reportlab
        # For now, return a notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Manifest Generated'),
                'message': _('PDF manifest generated for %d shipments') % len(self.shipment_ids),
                'type': 'success',
                'sticky': True,
            }
        }

    def _generate_csv(self, manifest_data):
        """Generate CSV manifest"""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Write headers
        headers = ['Reference', 'Carrier', 'Service', 'Tracking', 'Recipient', 'Weight', 'Packages', 'Cost', 'Status']
        writer.writerow(headers)

        # Write data
        for shipment in manifest_data['shipments']:
            writer.writerow([
                shipment['reference'],
                shipment['carrier'],
                shipment['service'],
                shipment['tracking'],
                shipment['recipient'],
                shipment['weight'],
                shipment['packages'],
                shipment['cost'],
                shipment['state'],
            ])

        csv_data = output.getvalue()

        return {
            'type': 'ir.actions.act_url',
            'url': f"/web/binary/download?data={base64.b64encode(csv_data.encode()).decode()}&filename=manifest.csv",
            'target': 'new',
        }

    def _generate_excel(self, manifest_data):
        """Generate Excel manifest"""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Manifest"

            # Headers
            headers = ['Reference', 'Carrier', 'Service', 'Tracking', 'Recipient', 'Weight', 'Packages', 'Cost',
                       'Status']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")

            # Data
            row_num = 2
            for shipment in manifest_data['shipments']:
                ws.cell(row=row_num, column=1, value=shipment['reference'])
                ws.cell(row=row_num, column=2, value=shipment['carrier'])
                ws.cell(row=row_num, column=3, value=shipment['service'])
                ws.cell(row=row_num, column=4, value=shipment['tracking'])
                ws.cell(row=row_num, column=5, value=shipment['recipient'])
                ws.cell(row=row_num, column=6, value=shipment['weight'])
                ws.cell(row=row_num, column=7, value=shipment['packages'])
                ws.cell(row=row_num, column=8, value=shipment['cost'])
                ws.cell(row=row_num, column=9, value=shipment['state'])
                row_num += 1

            # Auto-fit columns
            for col in range(1, len(headers) + 1):
                ws.column_dimensions[chr(64 + col)].width = 20

            # Save
            excel_data = BytesIO()
            wb.save(excel_data)
            excel_data.seek(0)

            return {
                'type': 'ir.actions.act_url',
                'url': f"/web/binary/download?data={base64.b64encode(excel_data.getvalue()).decode()}&filename=manifest.xlsx",
                'target': 'new',
            }

        except Exception as e:
            raise UserError(_('Failed to generate Excel: %s') % str(e))
