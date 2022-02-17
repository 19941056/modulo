# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _name = 'cits.config.settings'
    _inherit = 'res.config.settings'

    enable_notify_reminder = fields.Boolean("Enable to send mail reminder before appointment")
    notify_reminder_mail_template = fields.Many2one(
        "mail.template", string="Mail Notification Reminder", domain="[('model_id.model','=','cits.admin')]")
    enable_notify_customer_on_approve_appoint = fields.Boolean("Enable to send mail on Appointment Confirmation")
    notify_customer_on_approve_appoint = fields.Many2one(
        "mail.template", string="Appointment Confirmation Mail", domain="[('model_id.model','=','cits.admin')]")
    enable_notify_customer_on_reject_appoint = fields.Boolean("Enable to send mail on Appointment Reject")
    notify_customer_on_reject_appoint = fields.Many2one(
        "mail.template", string="Appointment Reject Mail", domain="[('model_id.model','=','cits.admin')]")
    enable_notify_customer_on_new_appoint = fields.Boolean("Enable to send mail to customer on New Appointment")
    notify_customer_on_new_appoint = fields.Many2one(
        "mail.template", string="New Appointment Mail to Customer", domain="[('model_id.model','=','cits.admin')]")
    enable_notify_admin_on_new_appoint = fields.Boolean("Enable to send mail to admin on New Appointment")
    notify_admin_on_new_appoint = fields.Many2one(
        "mail.template", string="New Appointment Mail to Admin", domain="[('model_id.model','=','cits.admin')]")

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('cits.config.settings', 'enable_notify_reminder', self.enable_notify_reminder)
        IrDefault.set('cits.config.settings', 'notify_reminder_mail_template',
                      self.notify_reminder_mail_template.id)
        IrDefault.set('cits.config.settings', 'enable_notify_customer_on_approve_appoint',
                      self.enable_notify_customer_on_approve_appoint)
        IrDefault.set('cits.config.settings', 'notify_customer_on_approve_appoint',
                      self.notify_customer_on_approve_appoint.id)
        IrDefault.set('cits.config.settings', 'enable_notify_customer_on_reject_appoint',
                      self.enable_notify_customer_on_reject_appoint)
        IrDefault.set('cits.config.settings', 'notify_customer_on_reject_appoint',
                      self.notify_customer_on_reject_appoint.id)
        IrDefault.set('cits.config.settings', 'enable_notify_customer_on_new_appoint',
                      self.enable_notify_customer_on_new_appoint)
        IrDefault.set('cits.config.settings', 'notify_customer_on_new_appoint',
                      self.notify_customer_on_new_appoint.id)
        IrDefault.set('cits.config.settings', 'enable_notify_admin_on_new_appoint',
                      self.enable_notify_admin_on_new_appoint)
        IrDefault.set('cits.config.settings', 'notify_admin_on_new_appoint', self.notify_admin_on_new_appoint.id)
        return True

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        appoint_reminder_mail_template = self.env['ir.model.data'].get_object_reference(
            'citas', 'reminder_mail_to_customer')[1]
        notify_customer_on_approve_appoint = self.env['ir.model.data'].get_object_reference(
            'citas', 'appoint_mgmt_email_template_to_customer')[1]
        notify_customer_on_reject_appoint = self.env['ir.model.data'].get_object_reference(
            'citas', 'appoint_mgmt_reject_email_template_to_customer')[1]
        notify_customer_on_new_appoint = self.env['ir.model.data'].get_object_reference(
            'citas', 'appoint_mgmt_new_appoint_mail_to_customer')[1]
        notify_admin_on_new_appoint = self.env['ir.model.data'].get_object_reference(
            'citas', 'appoint_mgmt_new_appoint_mail_to_admin')[1]
        IrDefault = self.env['ir.default'].sudo()

        res.update({
            'enable_notify_reminder': IrDefault.get('cits.config.settings', 'enable_notify_reminder'),
            'notify_reminder_mail_template': IrDefault.get('cits.config.settings',
                                                           'notify_reminder_mail_template')
                                             or appoint_reminder_mail_template,
            'enable_notify_customer_on_approve_appoint': IrDefault.get('cits.config.settings',
                                                                       'enable_notify_customer_on_approve_appoint'),
            'notify_customer_on_approve_appoint': IrDefault.get('cits.config.settings',
                                                                'notify_customer_on_approve_appoint')
                                                  or notify_customer_on_approve_appoint,
            'enable_notify_customer_on_reject_appoint': IrDefault.get('cits.config.settings',
                                                                      'enable_notify_customer_on_reject_appoint'),
            'notify_customer_on_reject_appoint': IrDefault.get('cits.config.settings',
                                                               'notify_customer_on_reject_appoint')
                                                 or notify_customer_on_reject_appoint,
            'enable_notify_customer_on_new_appoint': IrDefault.get('cits.config.settings',
                                                                   'enable_notify_customer_on_new_appoint'),
            'notify_customer_on_new_appoint': IrDefault.get('cits.config.settings',
                                                            'notify_customer_on_new_appoint')
                                              or notify_customer_on_new_appoint,
            'enable_notify_admin_on_new_appoint': IrDefault.get('cits.config.settings',
                                                                'enable_notify_admin_on_new_appoint'),
            'notify_admin_on_new_appoint': IrDefault.get('cits.config.settings', 'notify_admin_on_new_appoint')
                                           or notify_admin_on_new_appoint,
        })
        return res
