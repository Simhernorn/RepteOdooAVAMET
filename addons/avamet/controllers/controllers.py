# -*- coding: utf-8 -*-
# from odoo import http


# class Avamet(http.Controller):
#     @http.route('/avamet/avamet', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/avamet/avamet/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('avamet.listing', {
#             'root': '/avamet/avamet',
#             'objects': http.request.env['avamet.avamet'].search([]),
#         })

#     @http.route('/avamet/avamet/objects/<model("avamet.avamet"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('avamet.object', {
#             'object': obj
#         })

