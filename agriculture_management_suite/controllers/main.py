# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class FarmPortal(http.Controller):

    @http.route(['/farm/traceability/<string:code>'], type='http', auth='public', website=True)
    def traceability_query(self, code, **kw):
        harvest = request.env['farm.harvest'].sudo().search([('traceability_code', '=', code)], limit=1)
        if not harvest:
            return request.render('agriculture_management.traceability_not_found', {})

        # Gather traceability chain
        cultivation = harvest.cultivation_id
        inputs = cultivation.input_ids.sorted('application_date')

        values = {
            'harvest': harvest,
            'cultivation': cultivation,
            'field': cultivation.field_id,
            'crop': cultivation.crop_id,
            'season': harvest.season_id,
            'inputs': inputs,
        }
        return request.render('agriculture_management.traceability_report_public', values)
