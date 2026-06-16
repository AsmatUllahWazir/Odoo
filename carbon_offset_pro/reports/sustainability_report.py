from odoo import models, api


class SustainabilityReportPDF(models.AbstractModel):
    _name = 'report.carbon_offset_pro.report_sustainability_template'
    _description = 'Sustainability Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['sale.order'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': docs,
        }


class CarbonCertificatePDF(models.AbstractModel):
    _name = 'report.carbon_offset_pro.report_certificate_template'
    _description = 'Carbon Offset Certificate'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['carbon.offset.purchase'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'carbon.offset.purchase',
            'docs': docs,
        }
    