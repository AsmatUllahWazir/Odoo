# -*- coding: utf-8 -*-
# from odoo import http


# class ZakatWaqfPro(http.Controller):
#     @http.route('/zakat_waqf_pro/zakat_waqf_pro', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zakat_waqf_pro/zakat_waqf_pro/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zakat_waqf_pro.listing', {
#             'root': '/zakat_waqf_pro/zakat_waqf_pro',
#             'objects': http.request.env['zakat_waqf_pro.zakat_waqf_pro'].search([]),
#         })

#     @http.route('/zakat_waqf_pro/zakat_waqf_pro/objects/<model("zakat_waqf_pro.zakat_waqf_pro"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zakat_waqf_pro.object', {
#             'object': obj
#         })

