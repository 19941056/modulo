# -*- coding: utf-8 -*-
from odoo import http

# class Citas(http.Controller):
#     @http.route('/citas/citas/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/citas/citas/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('citas.listing', {
#             'root': '/citas/citas',
#             'objects': http.request.env['citas.citas'].search([]),
#         })

#     @http.route('/citas/citas/objects/<model("citas.citas"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('citas.object', {
#             'object': obj
#         })
