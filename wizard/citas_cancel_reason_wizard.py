import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class AppointRejectReason(models.TransientModel):
    _name = "cits.cancelreason.wizard"
    _description = "Appointment Cancel Reason"

    add_reason = fields.Text(string="Reason for Cancellation")

    @api.multi
    def button_addreason(self):
        obj = self.env['cits.admin'].browse(self._context.get('active_ids'))
        if obj:
            add_reason = "Reason for Cancellation of Appointment : " + self.add_reason
            obj.cancel_cits(add_reason)
        return
