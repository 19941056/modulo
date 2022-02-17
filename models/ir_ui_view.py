from odoo import api, models, fields

TIMELINE_VIEW = ('cits_timeline', 'Timeline')


class IrUIView(models.Model):
    _inherit = 'ir.ui.view'

    type = fields.Selection(selection_add=[TIMELINE_VIEW])
