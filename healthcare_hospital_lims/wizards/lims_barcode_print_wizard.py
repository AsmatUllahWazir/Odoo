# -*- coding: utf-8 -*-
"""
Barcode Print Wizard
Generates and prints barcode labels for samples
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
from io import BytesIO


class LimsBarcodePrintWizard(models.TransientModel):
    """
    Wizard for printing sample barcodes
    """
    _name = 'lims.barcode.print.wizard'
    _description = 'Barcode Print Wizard'

    sample_id = fields.Many2one(
        'lims.sample',
        string='Sample',
        required=True
    )

    barcode_format = fields.Selection([
        ('code128', 'Code 128'),
        ('code39', 'Code 39'),
        ('ean13', 'EAN-13'),
        ('upc', 'UPC-A')
    ], string='Barcode Format', default='code128')

    print_quantity = fields.Integer(
        string='Print Quantity',
        default=2,
        help='Number of labels to print'
    )

    include_patient = fields.Boolean(
        string='Include Patient Name',
        default=True
    )

    include_order = fields.Boolean(
        string='Include Order ID',
        default=True
    )

    include_barcode_text = fields.Boolean(
        string='Include Barcode Text',
        default=True
    )

    label_size = fields.Selection([
        ('small', 'Small (2x1 inch)'),
        ('medium', 'Medium (3x1.5 inch)'),
        ('large', 'Large (4x2 inch)')
    ], string='Label Size', default='medium')

    preview_barcode = fields.Binary(
        string='Preview',
        compute='_compute_preview_barcode'
    )

    @api.depends('sample_id', 'barcode_format')
    def _compute_preview_barcode(self):
        """Generate preview barcode image"""
        for record in self:
            if record.sample_id and record.sample_id.barcode:
                try:
                    import barcode
                    from barcode.writer import ImageWriter

                    code = barcode.get_barcode_class(record.barcode_format)
                    barcode_instance = code(record.sample_id.barcode, writer=ImageWriter())
                    buffer = BytesIO()
                    barcode_instance.write(buffer, {
                        'format': 'PNG',
                        'module_width': 0.2,
                        'module_height': 15,
                        'quiet_zone': 4,
                    })
                    buffer.seek(0)
                    record.preview_barcode = base64.b64encode(buffer.getvalue())
                except Exception:
                    record.preview_barcode = False
            else:
                record.preview_barcode = False

    def action_print_barcode(self):
        """Generate and print barcode labels"""
        self.ensure_one()
        sample = self.sample_id

        # Generate barcode data
        barcode_data = {
            'sample_id': sample.sample_id,
            'patient_name': sample.patient_name if self.include_patient else '',
            'order_id': sample.test_order_id.order_id if self.include_order else '',
            'barcode': sample.barcode,
            'sample_type': dict(sample._fields['sample_type'].selection).get(sample.sample_type),
            'collection_date': sample.collection_date.strftime('%Y-%m-%d') if sample.collection_date else '',
        }

        # This would trigger a report for barcode printing
        return self.env.ref('hospital_lims.action_report_lims_barcode').report_action(
            self, data={
                'barcode_data': barcode_data,
                'quantity': self.print_quantity,
                'label_size': self.label_size,
                'include_barcode_text': self.include_barcode_text,
            }
        )
    