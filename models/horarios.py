# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.tools import UserError

from datetime import datetime, timedelta


class HrEmployeeSch(models.Model):
    _inherit = 'hr.employee'

    schedule_ids = fields.One2many('specialist.schedule', 'specialist_id', 'Specialist Schedule Planning')

    


class Schedules(models.Model):
    _name = 'specialist.schedule'
    _description = 'Specialist Schedule'

    specialist_id = fields.Many2one('hr.employee', string="Especialista", required=True)
    start_date = fields.Datetime('Fecha y Hora de Inicio')
    date_delay = fields.Float('Duración')

    @api.constrains('date_delay')
    def range_duration(self):
        for rec in self:
            if rec.date_delay < 4 or rec.date_delay > 11:
                raise UserError(_("La duración del horario no puede ser menor de 4 o mayor de 11 horas."))

    @api.model_create_multi
    def create(self, vals):
        records = super(Schedules, self).create(vals)
        for r in records:
            fmt = "%Y-%m-%d %H:%M:%S"
            date_end = (datetime.strptime(str(r.start_date), fmt) + timedelta(hours=r.date_delay))
            vdate = datetime.strptime(str(r.start_date), fmt).date()
            vals_list = {
                'appoint_employ_id': r.specialist_id.id,
                'date_start': r.start_date,
                'duration': r.date_delay,
                'date_end': date_end,
                'appoint_date': vdate,
                'sch_id': r.id,
            }
            self.env['cits.admin'].create(vals_list)
        return records

    @api.multi
    def write(self, vals):
        record = super(Schedules, self).write(vals)
        fmt = "%Y-%m-%d %H:%M:%S"
        date_end = (datetime.strptime(str(self.start_date), fmt) + timedelta(hours=self.date_delay))
        vdate = datetime.strptime(str(self.start_date), fmt).date()
        vals_list = {
            'date_start': self.start_date,
            'duration': self.date_delay,
            'date_end': date_end,
            'appoint_date': vdate,
        }
        self.env['cits.admin'].sudo().search([('sch_id', '=', self.id)]).write(vals_list)
        return record

    @api.multi
    def unlink(self):
        fmt = "%Y-%m-%d %H:%M:%S"
        date_end = (datetime.strptime(str(self.start_date), fmt) + timedelta(hours=self.date_delay))
        #hay que buscar las citas relacionadas al empleado, y si hay alguna dentro del span no se puede borrar
        citas = self.env['cits.admin'].sudo().search([
            ('appoint_employ_id','=',self.specialist_id.id),
            ('habitation','!=',False),
        ])
        if citas != [] and citas != False and citas!= None:
            for cita in citas:
                if (cita.date_start >= self.start_date and cita.date_end <= date_end) or (cita.date_start < self.start_date and cita.date_end >= self.start_date) or (cita.date_start < date_end and cita.date_end >= date_end):
                    #entra dentro del span, no podemos eliminar
                    raise UserError(_("El especialista ya tiene asignada una cita en esta franja horaria. Por favor, elimina primero las citas."))
        
        res = super(Schedules, self).unlink()
        self.env['cits.admin'].sudo().search([('sch_id', '=', self.id)]).unlink()
        return res

    #@api.onchange('start_date')
    def checkNoCits(self):
        originalDate = self._origin.start_date
        fmt = "%Y-%m-%d %H:%M:%S"
        date_end = (datetime.strptime(str(originalDate), fmt) + timedelta(hours=self.date_delay))
        #hay que buscar las citas relacionadas al empleado, y si hay alguna dentro del span no se puede cambiar la hora
        citas = self.env['cits.admin'].sudo().search([
            ('appoint_employ_id','=',self._origin.specialist_id.id),
            ('habitation','!=',False),
        ])
        raise UserError(_("original date "+ str(originalDate) + " current date "+ str(self.start_date)))

        if len(citas) != 0: #citas != [] and citas != False and citas!= None:
            for cita in citas:
                if (cita.date_start >= originalDate and cita.date_end <= date_end) or (cita.date_start < originalDate and cita.date_end >= originalDate) or (cita.date_start < date_end and cita.date_end >= date_end):
                    #entra dentro del span, no podemos mover la dita
                    raise UserError(_("El especialista ya tiene asignada una cita en esta franja horaria. Por favor, elimina primero las citas."))
        

