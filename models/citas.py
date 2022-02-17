# -*- coding: utf-8 -*-
import math
from datetime import date, time, datetime, timedelta

from odoo import models, fields, api, _
from odoo.tools import relativedelta, UserError, float_round


def float_to_time(hours):
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)


class CitsAdmin(models.Model):
    _name = 'cits.admin'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc, date_start desc'
    _description = "Gestion de Citas"

    name = fields.Char(string="Number", default='Nuevo', copy=False)
    customer = fields.Many2one("res.partner", 'Paciente')
    appoint_employ_id = fields.Many2one('hr.employee', string='Especialista', track_visibility="onchange")
    product_id = fields.Many2one('product.product', string='Servicio', track_visibility="onchange")
    date_start = fields.Datetime('Fecha y Hora de Inicio de la Cita', default=fields.Datetime.now(),
                                 track_visibility="onchange")
    date_end = fields.Datetime('Fecha y Hora de Finalización de la Cita', compute='_fecha_final', store=True)
    duration = fields.Float('Duración', default='1.0')
    appoint_date = fields.Date('Fecha de la Cita', compute='_fecha_corta', store=True)
    date_delay = fields.Char('Duración', compute='_duracion', store=True)
    appoint_state = fields.Selection([('approved', 'Aprobada'),
                                      ('canceled', 'Cancelada'),
                                      ('done', 'Done')], string="State", default="approved",
                                     track_visibility="onchange", copy=False)
    habitation = fields.Many2one('habitations.source', string='Cabinas')
    description = fields.Text('Descripciónn', copy=False)
    color = fields.Integer('Color')
    sch_id = fields.Integer('ID Horario')
    enable_notify_reminder = fields.Boolean(string="Notify using Mail",
                                            default=lambda self: self.env['ir.default'].sudo().get(
                                                'cits.config.settings', 'enable_notify_reminder'))
    remind_in = fields.Selection([('days', 'Dia(s)'), ('hours', 'Hora(s)')], string="Remind In", default="days")
    remind_time = fields.Integer(string="Reminder Time", default=1)
    is_mail_sent = fields.Boolean("Reminder Mail Send", copy=False)
    notify_customer_on_approve_appoint = fields.Boolean('Notify Customer on New Appointment',
                                                        default=lambda self: self.env['ir.default'].get(
                                                            "cits.config.settings",
                                                            'notify_customer_on_approve_appoint')
                                                        )
    notify_customer_on_reject_appoint = fields.Boolean('Notify Customer on Appointment Reject',
                                                       default=lambda self: self.env['ir.default'].get(
                                                           "cits.config.settings",
                                                           'notify_customer_on_reject_appoint')
                                                       )
    cancel_reason = fields.Char("Cancel Reason")

    @api.depends('date_start')
    def _fecha_corta(self):
        fmt = "%Y-%m-%d %H:%M:%S"
        for rec in self:
            if rec.date_start:
                rec.appoint_date = datetime.strptime(str(rec.date_start), fmt).date()

    @api.depends('date_start', 'duration')
    def _fecha_final(self):
        fmt = "%Y-%m-%d %H:%M:%S"
        for rec in self:
            if rec.date_start:
                rec.date_end = (datetime.strptime(str(rec.date_start), fmt) + timedelta(hours=rec.duration))

    @api.depends('date_start')
    def _duracion(self):
        fmt = "%d-%m-%Y %H:%M"
        for r in self:
            da_dl = datetime.strptime(str(r.date_start), "%Y-%m-%d %H:%M:%S") + timedelta(hours=2)
            r.date_delay = datetime.strftime(da_dl, fmt)

    @api.onchange('appoint_employ_id')
    def compute_val_date(self):
        fmt = "%Y-%m-%d %H:%M:%S"
        appoint_date = datetime.strptime(str(self.date_start), fmt)
        appoint_dt = datetime.strftime(appoint_date, fmt)
        dt1 = datetime.strptime(appoint_dt, fmt)
        dtw = datetime.strptime(appoint_dt, fmt).weekday()
        dt2 = datetime.now().strftime(fmt)
        dt3 = datetime.strptime(dt2, fmt)
        rdt = relativedelta(dt3, dt1)
        if not dtw == 6:
            if rdt.years > 0 or rdt.months > 0 or rdt.days > 0 or rdt.hours > 0 or rdt.minutes > 5:
                raise UserError(_("La fecha y/o hora de la cita no puede ser anterior a hoy."))
        else:
            raise UserError(_("Seleccionar los días de Lunes a Sábado."))

    @api.onchange('appoint_employ_id','duration')
    def compute_val_time(self):
        available_time = self.env['hr.employee'].sudo().search([
            ('id','=',self.appoint_employ_id.id)
            ])[0].schedule_ids
        fmt = "%Y-%m-%d %H:%M:%S"
        appoint_date = datetime.strptime(str(self.date_start), fmt)
        appoint_dt = datetime.strftime(appoint_date, fmt)
        dt1 = datetime.strptime(appoint_dt, fmt)
        dtd = datetime.strptime(appoint_dt, fmt).date() #fecha sin hora
        obj_emp = self.sudo().search([ #cogemos citas con fecha igual a la cita que se intenta,       #y mismo especialista
            ('appoint_date', '=', dtd),
            ('habitation', '!=', self.habitation.id),
            ('appoint_employ_id', '=', self.appoint_employ_id.id)])
        if obj_emp:
            for obj in obj_emp:
                if (self.habitation.id != False) and ((self.date_start >= obj.date_start and self.date_end <= obj.date_end) or (self.date_start < obj.date_start and self.date_end >= obj.date_start) or (self.date_start < obj.date_end and self.date_end >= obj.date_end)):
                    raise UserError(_("El especialista ya tiene asignada una cita en otra cabina."))
        #tenemos que comprobar que la fecha de start sea despues del inicio de alguna fecha de entrada
        #y que la fecha de end sea anterior a la fecha de salida 
        raise_error = True
        if available_time:
            for time_span in available_time:
                end_date = datetime.strptime(str(time_span.start_date), "%Y-%m-%d %H:%M:%S") + timedelta(hours=time_span.date_delay)
                if (self.date_start >= time_span.start_date and self.date_end <= end_date)  :
                    raise_error = False
        else: raise_error = True
        if raise_error : raise UserError(_("Seleccionar los dias y horas hábiles de los especialistas."))
   
    
    def compute_val_overlap(self):
        fmt = "%Y-%m-%d %H:%M:%S"
        appoint_date = datetime.strptime(str(self.date_start), fmt)
        appoint_dt = datetime.strftime(appoint_date, fmt)
        dtd = datetime.strptime(appoint_dt, fmt).date()
        dt1 = datetime.strptime(appoint_dt, fmt)
        dte = (datetime.strptime(str(appoint_dt), fmt) + timedelta(hours=self.duration))
        appoint_obj = self.sudo().search([
            ('id', '!=', self.id),
            ('name', '!=', False),
            ('appoint_date', '=', dtd),
            ('appoint_employ_id', '=', self.appoint_employ_id.id)])
        if appoint_obj:
            for app in appoint_obj:
                if app.date_start == dt1 and dte == app.date_end:
                    raise UserError(
                        _("Ya se aprobó una cita en la misma fecha y franja horaria para este especialista."))
                elif app.date_start < dt1 < app.date_end:
                    raise UserError(
                        _("Ya se aprobó una cita en la misma fecha y franja horaria para este especialista."))
                elif app.date_start < dte < app.date_end:
                    raise UserError(
                        _("Ya se aprobó una cita en la misma fecha y franja horaria para este especialista."))

    @api.onchange('date_start')
    def compute_employ(self):
        fmt = "%Y-%m-%d %H:%M:%S"
        appoint_date = datetime.strptime(str(self.date_start), fmt)
        appoint_dt = datetime.strftime(appoint_date, fmt)
        dtd = datetime.strptime(appoint_dt, fmt).date()
        dt1 = datetime.strptime(appoint_dt, fmt)
        dt2 = (datetime.strptime(str(appoint_dt), fmt) + timedelta(hours=self.duration))
        employ = []
        emp_obj = self.sudo().search([('name', '=', False), ('appoint_date', '=', dtd)])
        appointed = []
        appoint_obj = self.sudo().search([
            ('name', '!=', False),
            ('appoint_date', '=', dtd),
            ('appoint_state', '=', 'approved')])
        if emp_obj:
            for rec in emp_obj:
                if rec.date_start <= dt1 <= rec.date_end:
                    employ.append(rec.appoint_employ_id.id)
                if appoint_obj:
                    for app in appoint_obj:
                        if app.date_start == dt1 and dt2 == app.date_end:
                            appointed.append(app.appoint_employ_id.id)
                        elif app.date_start < dt1 < app.date_end:
                            appointed.append(app.appoint_employ_id.id)
                        elif app.date_start < dt2 < app.date_end:
                            appointed.append(app.appoint_employ_id.id)
            res = {'domain': {'appoint_employ_id': [
                '&', ('id', 'in', employ), ('id', 'not in', appointed)]}}
            return res

    @api.onchange('date_start', 'duration')
    def compute_cabin(self):
        fmt = "%Y-%m-%d %H:%M:%S"
        app_date = datetime.strptime(str(self.date_start), fmt)
        app_dt = datetime.strftime(app_date, fmt)
        dtd = datetime.strptime(app_dt, fmt).date()
        dt1 = datetime.strptime(app_dt, fmt)
        dt2 = (datetime.strptime(str(app_dt), fmt) + timedelta(hours=self.duration))
        cabin = []
        cab_obj = self.env['habitations.source'].sudo().search([])
        appointed = []
        appoint_obj = self.sudo().search([('name', '!=', False), ('appoint_date', '=', dtd)])
        if cab_obj:
            for cab in cab_obj:
                cabin.append(cab.id)
            if appoint_obj:
                for app in appoint_obj:
                    if (self.date_start >= app.date_start and self.date_end <= app.date_end) or (self.date_start < app.date_start and self.date_end > app.date_start) or (self.date_start < app.date_end and self.date_end > app.date_end):
                        appointed.append(app.habitation.id)
                    
            res = {'domain': {'habitation': [
                '&', ('id', 'in', cabin), ('id', 'not in', appointed)]}}
            return res

    @api.multi
    def send_approve_cits_mail(self):
        for rec in self:
            if rec.notify_customer_on_approve_appoint:
                template_id = self.sudo().env.ref("citas.appoint_mgmt_email_template_to_customer")
                template_id.send_mail(rec.id, force_send=True)

    @api.multi
    def button_approve_appoint(self):
        if self.appoint_employ_id:
            appointment_obj = self.sudo().search([
                ("date_start", '=', self.date_start),
                ("appoint_employ_id", '=', self.appoint_employ_id.id),
                ("duration", '=', self.duration),
                ("habitation", "=", self.habitation.id),
                ("appoint_state", "in", ['approved']),
            ])
            if appointment_obj:
                raise UserError(_("Ya se aprobó una cita para esta persona designada en la misma fecha y franja "
                                  "horaria."))
        self.compute_appdate()
        self.write({'appoint_state': 'approved'})
        self.send_approve_cits_mail()
        return True

    @api.multi
    def button_set_to_pending(self):
        self.write({'appoint_state': 'pending'})
        return True

    @api.multi
    def button_done_appoint(self):
        for rec in self:
            current_date = date.today()
            later_date = datetime.strptime(str(rec.date_start), "%Y-%m-%d %H:%M:%S").date()
            time_diff = relativedelta(later_date, current_date)
            if time_diff.days > 0 or time_diff.months > 0 or time_diff.years > 0:
                raise UserError(_("La cita no se puede completar antes de su fecha."))
        self.write({'appoint_state': 'done'})
        return True

    @api.multi
    def button_reject_appoint_action(self):
        # view_id = self.env["cits.cancelreason.wizard"]
        # values = {
        #     'name': _("Mention reason to cancel appointment"),
        #     'view_mode': 'form',
        #     'view_type': 'form',
        #     'res_model': 'cits.cancelreason.wizard',
        #     'res_id': view_id.id,
        #     'type': "ir.actions.act_window",
        #     'target': 'new',
        # }
        #return values

        #Esto necesita un dialog de confirmación.
        # obj = self.sudo().search([
        #         ("date_start", '=', self.date_start),
        #         ("appoint_employ_id", '=', self.appoint_employ_id.id),
        #         ("duration", '=', self.duration),
        #         ("habitation", "=", self.habitation.id),
        #         ("id","=",self.id),
        #     ], limit=1)
        self.unlink()
        return {
            'name' : 'Citas',
             'type': 'ir.actions.act_window',
            'res_model': 'cits.admin',
            'view_type': 'cits_timeline',
            'view_mode': 'cits_timeline',
            'target': 'current',
            'context': {'group_by': ['appoint_employ_id']},
        }

    @api.multi
    def cancel_cits(self, add_reason):
        self.ensure_one()
        self.cancel_reason = add_reason
        self.message_post(body=add_reason)
        self.write({'appoint_state': 'canceled'})
        if self.notify_customer_on_reject_appoint:
            template_id = self.sudo().env.ref("citas.appoint_mgmt_reject_email_template_to_customer")
            template_id.send_mail(self.id, force_send=True)

    @api.model
    def create(self, vals):
        # delay = vals.get('duration')
        # if not int(delay) or int(delay) < 4:
        hab = vals.get('habitation')
        if hab != None and hab != []:
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code("cits.admin")
            cits = super(CitsAdmin, self).create(vals)
            cits.compute_val_date()
            cits.compute_val_time()
            cits.send_new_appoint_mail()
            return cits
        else:
            vals['name'] = None
            vals['appoint_state'] = None
            cits = super(CitsAdmin, self).create(vals)
            return cits

    @api.multi
    def write(self, vals):
        for rec in self:
            res = super(CitsAdmin, self).write(vals)
            if vals.get("date_start"):
                rec.compute_val_date()
                rec.compute_val_time()
                rec.compute_val_overlap()
        return res

    def send_new_appoint_mail(self):
        for rec in self:
            template_obj = self.env['mail.template']
            cits_config_obj = self.env['cits.config.settings'].get_values()
            if cits_config_obj.get("enable_notify_customer_on_new_appoint") and cits_config_obj.get(
                    "notify_customer_on_new_appoint"):
                temp_id = cits_config_obj["notify_customer_on_new_appoint"]
                if not temp_id:
                    temp_id = self.sudo().env.ref("citas.appoint_mgmt_new_appoint_mail_to_customer")
                if temp_id:
                    template_obj.browse(temp_id).sudo().send_mail(rec.id, force_send=True)
            if cits_config_obj.get("enable_notify_admin_on_new_appoint") and cits_config_obj.get(
                    "notify_admin_on_new_appoint"):
                temp_id = cits_config_obj["notify_admin_on_new_appoint"]
                if not temp_id:
                    temp_id = self.sudo().env.ref("citas.appoint_mgmt_new_appoint_mail_to_admin")
                if temp_id:
                    template_obj.browse(temp_id).sudo().send_mail(rec.id, force_send=True)

    @api.one
    def send_reminder_mail_to_customer(self):
        template_obj = self.env['mail.template']
        cits_config_obj = self.env['cits.config.settings'].get_values()
        if cits_config_obj["enable_notify_reminder"] and cits_config_obj.get("notify_reminder_mail_template") and \
                cits_config_obj["notify_reminder_mail_template"]:
            temp_id = cits_config_obj["notify_reminder_mail_template"]
            if temp_id:
                template_obj.browse(temp_id).send_mail(self.id, force_send=True)
        return True

    @api.model
    def send_mail_for_reminder_scheduler_queue(self):
        obj = self.search([])
        for rec in obj:
            if rec.appoint_state == 'approved':
                if rec.enable_notify_reminder:
                    remind_time = rec.remind_time
                    if remind_time:
                        if rec.remind_in == 'days':
                            current_time = date.today()
                            later_time = datetime.strptime(str(rec.date_start), "%Y-%m-%d %H:%M:%S").date() - timedelta(
                                days=remind_time)
                            time_diff = relativedelta(later_time, current_time)
                            if time_diff.days == 0 and time_diff.months == 0 and time_diff.years == 0:
                                if not rec.is_mail_sent:
                                    rec.send_reminder_mail_to_customer()
                                    rec.is_mail_sent = True


class Habitations(models.Model):
    _name = 'habitations.source'
    _description = "Habitations"

    name = fields.Char("Habitations", required=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    citas_ids = fields.One2many('cits.admin', 'customer')
    count_cits = fields.Integer(compute='_compute_count_cits', string="Citas")

    def _compute_count_cits(self):
        for partner in self:
            partner.count_cits = len(partner.citas_ids.ids)

    def action_get_citas_tree_view(self):
        action = self.env.ref('citas.cit_mgmt_book_cits_action').read()[0]
        action['name'] = "Citas"
        action['domain'] = [('customer', '=', self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action
