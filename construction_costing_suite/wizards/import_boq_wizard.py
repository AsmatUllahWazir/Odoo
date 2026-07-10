# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import io
import logging

_logger = logging.getLogger(__name__)


class ImportBOQWizard(models.TransientModel):
    _name = 'import.boq.wizard'
    _description = 'Import BOQ from Excel'

    project_id = fields.Many2one('project.project', string='Project', required=True)
    boq_name = fields.Char(string='BOQ Name', required=True,
                           default=lambda self: _('BOQ %s') % fields.Date.today().strftime('%Y-%m-%d'))
    file_data = fields.Binary(string='Excel/CSV File', required=True, help="Upload Excel (.xlsx, .xls) or CSV file")
    file_name = fields.Char(string='File Name')
    import_mode = fields.Selection([
        ('create_new', 'Create New BOQ'),
        ('update_existing', 'Update Existing BOQ')
    ], string='Import Mode', default='create_new')
    existing_boq_id = fields.Many2one('construction.boq', string='Existing BOQ',
                                      domain="[('project_id', '=', project_id)]")
    skip_headers = fields.Boolean(string='Skip First Row', default=True, help="Check if the first row contains headers")

    product_column = fields.Integer(string='Product Column', default=0)
    quantity_column = fields.Integer(string='Quantity Column', default=1)
    price_column = fields.Integer(string='Price Column', default=2)
    description_column = fields.Integer(string='Description Column', default=3)
    category_column = fields.Integer(string='Category Column', default=4)

    @api.constrains('file_data')
    def _check_file_data(self):
        for wizard in self:
            if wizard.file_data:
                try:
                    data = base64.b64decode(wizard.file_data)
                    if len(data) == 0:
                        raise ValidationError(_("File is empty."))
                except Exception as e:
                    raise ValidationError(_("Invalid file format: %s") % str(e))

    def action_import(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError(_("Please select a file to import."))

        try:
            file_data = base64.b64decode(self.file_data)

            try:
                import pandas as pd
            except ImportError:
                raise UserError(_("Please install pandas library to use this feature."))

            if self.file_name and self.file_name.lower().endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_data), header=0 if self.skip_headers else None)
            else:
                df = pd.read_excel(io.BytesIO(file_data), header=0 if self.skip_headers else None)

            if df.empty:
                raise UserError(_("The file is empty or could not be parsed."))

            if self.import_mode == 'create_new':
                result = self._create_new_boq(df)
            else:
                if not self.existing_boq_id:
                    raise UserError(_("Please select an existing BOQ to update."))
                result = self._update_existing_boq(df, self.existing_boq_id)

            return result

        except Exception as e:
            _logger.error(f"Import BOQ error: {str(e)}")
            raise UserError(_("Error importing file: %s") % str(e))

    def _create_new_boq(self, df):
        boq_vals = {
            'name': self.boq_name,
            'project_id': self.project_id.id,
            'date': fields.Date.today(),
            'state': 'draft',
            'company_id': self.env.company.id,
        }
        boq = self.env['construction.boq'].create(boq_vals)
        lines_created = self._create_boq_lines(boq, df)

        if lines_created == 0:
            raise UserError(_("No valid lines were imported. Please check the file format."))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.boq',
            'res_id': boq.id,
            'view_mode': 'form',
            'context': {'form_view_initial_mode': 'edit'},
        }

    def _update_existing_boq(self, df, existing_boq):
        lines_created = self._create_boq_lines(existing_boq, df)

        if lines_created == 0:
            raise UserError(_("No valid lines were imported. Please check the file format."))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'construction.boq',
            'res_id': existing_boq.id,
            'view_mode': 'form',
        }

    def _create_boq_lines(self, boq, df):
        lines_created = 0
        BOQLine = self.env['construction.boq.line']
        Product = self.env['product.product']

        col_map = {
            'product': self.product_column,
            'quantity': self.quantity_column,
            'price': self.price_column,
            'description': self.description_column,
            'category': self.category_column,
        }

        for idx, row in df.iterrows():
            try:
                product_name = self._get_column_value(row, col_map['product'])
                if not product_name:
                    continue

                product = Product.search([('name', 'ilike', product_name)], limit=1)
                if not product:
                    product_vals = {
                        'name': product_name,
                        'type': 'product',
                        'default_code': f"BOQ_{idx}",
                        'uom_id': self.env.ref('uom.product_uom_unit').id,
                        'company_id': self.env.company.id,
                    }
                    product = Product.create(product_vals)

                quantity = float(self._get_column_value(row, col_map['quantity']) or 0.0)
                if quantity <= 0:
                    continue

                unit_price = float(self._get_column_value(row, col_map['price']) or 0.0)
                description = str(self._get_column_value(row, col_map['description']) or '')

                category_str = str(self._get_column_value(row, col_map['category']) or 'materials')
                category_map = {
                    'materials': 'materials',
                    'labor': 'labor',
                    'labour': 'labor',
                    'subcontractor': 'subcontractor',
                    'equipment': 'equipment',
                    'overhead': 'overhead',
                    'overheads': 'overhead',
                    'other': 'other'
                }
                category = category_map.get(category_str.lower().strip(), 'materials')

                line_vals = {
                    'boq_id': boq.id,
                    'product_id': product.id,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'description': description,
                    'category': category,
                    'uom_id': product.uom_id.id or self.env.ref('uom.product_uom_unit').id,
                    'sequence': (idx + 1) * 10,
                }

                BOQLine.create(line_vals)
                lines_created += 1

            except Exception as e:
                _logger.warning(f"Error importing row {idx}: {str(e)}")
                continue

        return lines_created

    def _get_column_value(self, row, column_index):
        try:
            if column_index < len(row):
                return row.iloc[column_index]
        except:
            pass
        return None
