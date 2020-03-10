#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# from odoo import api
# -*- coding: utf-8 -*-


from odoo import models, fields, api, _
from odoo.tools import float_is_zero
import re
import ast
from datetime import date, datetime, time, timedelta
import calendar
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import logging
from odoo import SUPERUSER_ID
_logger = logging.getLogger(__name__)

HOURS_PER_DAY = 8

class hr_holidays(models.Model):
    _inherit = 'hr.leave'

    number_of_hours_temp = fields.Float('Numero de Horas')
    
    @api.multi
    @api.onchange('date_to', 'date_from')
    def onchange_date_from(self):
        
        date_from = self.date_from
        date_to = self.date_to

        # No date_to set so far: automatically compute one 8 hours later
        if date_from and not date_to:
            date_to_with_delta = fields.Datetime.from_string(date_from) + timedelta(hours=HOURS_PER_DAY)
            self.date_to = str(date_to_with_delta)
   
        # Compute and update the number of days
        if (date_to and date_from) and (date_from <= date_to):
            _date_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            _date_to = datetime.combine(fields.Date.from_string(date_to), time.max)
            dates = _date_to - _date_from

            diff_day = dates.days

            self.number_of_days = diff_day
        else:
            self.number_of_days = 0
         

    @api.multi
    @api.onchange('number_of_hours_temp')
    def onchange_days_hours(self):
        
        hours = self.number_of_hours_temp
        if self.request_hour_from:
            if self.request_hour_from > 0:
                
                self.request_hour_to = self.request_hour_from + hours
            else:
                self.request_hour_to = self.request_hour_from - hours   
        
        self.number_of_days_temp =  self.number_of_hours_temp 
        self.number_of_hours_display = self.number_of_days_temp 


    @api.multi
    @api.onchange('request_hour_from', 'request_hour_to')
    def onchange_hours(self):
        self.number_of_hours_temp = 0
        total_hours =  0
        if self.request_hour_from:
            hour_start = self.request_hour_from
            hour_end = self.request_hour_to
            if hour_start > 0:
                if self.request_hour_to > 0: 
                    total_hours = hour_end - hour_start
                else:
                    total_hours = ((hour_end + hour_start) + 0.5)*-1

            else:
                if self.request_hour_to > 0: 
                    total_hours = hour_end + hour_start
                else:
                    total_hours = ((hour_end - hour_start) + 0.5) *-1

        self.number_of_hours_temp = total_hours
        self.number_of_days_temp = total_hours
        self.number_of_hours_display = self.number_of_hours_temp 


class calendar_event_type(models.Model):
    _inherit = 'calendar.event.type'

    notunaffected_days = fields.Boolean('No Afecta Dias Laborados')
    is_hours_additional = fields.Boolean('Horas Extras')

class calendar_event_type(models.Model):
    _inherit = 'hr.leave.type'

    is_hollidays = fields.Boolean('Es Vacaciones')
