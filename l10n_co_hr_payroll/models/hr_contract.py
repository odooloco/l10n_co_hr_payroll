import logging
_logger = logging.getLogger(__name__)
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo.osv import osv
from odoo.exceptions import UserError, ValidationError
from datetime import *
import logging
_logger = logging.getLogger(__name__)


class hr_employee_category(models.Model):
    _inherit = 'hr.contract' 
    
    salario_minimo = fields.Float('Salario Minimo Vigente')
    aux_transporte = fields.Float('Auxilio de Transporte')
    salario_minimo_r = fields.Float('Salario Minimo Vigente', related = 'salario_minimo', readonly= True)
    aux_transporte_r = fields.Float('Auxilio de Transporte', related = 'aux_transporte', readonly= True)      
    base_sal_min = fields.Boolean('Base Salario Minimo')
    hollidays_ids = fields.One2many('holidays.record','contract_id','Holidays')
    
    @api.model
    def hollidays_cron(self):
        
        contract_model = self.env['hr.contract']
        consult_contract = contract_model.search([('type_id','=', 1), ('state','!=', 'close')])

        for contract in consult_contract:
            _holidays= []
            real_year = datetime.now()
            last_year = real_year - timedelta(days=365)
            year_contract = fields.Datetime.from_string(contract.date_start)
            _state = 'pending'
            if last_year.year >= year_contract.year:
                _ini_date_hollidays = datetime.strptime('%s-%s-%s' % ( last_year.year, year_contract.month, year_contract.day), "%Y-%m-%d")
                _fin_date_hollidays = _ini_date_hollidays + timedelta(days=364)
                _hollidays_id = 0
                _date_ini_attendance = False
                _date_end_attendance =  False
                _paylist = False

                model_hollidays = self.env['hr.leave']
                consult_holidays = model_hollidays.search([('employee_id', '=', contract.employee_id.id)])
                model_payroll = self.env['hr.payslip']
                consult_payroll = model_payroll.search([('employee_id', '=', contract.employee_id.id)])
                model_holidays_satus = self.env['hr.leave.status']
                modeL_ir_traslation = self.env['ir.translation']
                
                for absence in consult_holidays:
                    if absence.holiday_status_id.is_hollidays:
                      
                        _fin_holidays = _fin_date_hollidays + timedelta(days=365)
                
                        if absence.date_from >= str(_fin_date_hollidays) and absence.date_to <= str(_fin_holidays):
                            _state = 'programmed'
                            _hollidays_id = absence.id
                            _date_ini_attendance = absence.date_from
                            _date_end_attendance =  absence.date_to
                            for payslip in consult_payroll:
                                for work_line in payslip.worked_days_line_ids:
                                    consul_ir_traslation = modeL_ir_traslation.search([('value', '=', work_line.code),('name','=', 'hr.leave.status,name')])
                                    for traslation in consul_ir_traslation:
                                        if traslation.src == absence.holiday_status_id.name:
                                            _paylist = payslip.id
                                            _state = 'liquidated'
                        else:
                            template_id_model = self.env['mail.template']
                            template_id = template_id_model.sudo().search([('name', '=', 'Holidays Pending')])                    
                            template_id.send_mail(contract.id, True)

                if contract.hollidays_ids:
                    for holli in contract.hollidays_ids:
                        if datetime.strptime(holli.ini_date_hollidays, "%Y-%m-%d") == _ini_date_hollidays and datetime.strptime(holli.fin_date_hollidays,"%Y-%m-%d") == _fin_date_hollidays:
                            _holidays.append((1, holli.id, {
                                        'ini_date_hollidays': _ini_date_hollidays,
                                        'fin_date_hollidays': _fin_date_hollidays,
                                        'hollidays_id': _hollidays_id,
                                        'date_ini_attendance': _date_ini_attendance,
                                        'date_end_attendance': _date_end_attendance,
                                        'payslip_id': _paylist,
                                        'contract_id': contract.id,
                                        'state' : _state
                                    }))
                        else:
                            _holidays.append((0, 0, {
                                        'ini_date_hollidays': _ini_date_hollidays,
                                        'fin_date_hollidays': _fin_date_hollidays,
                                        'hollidays_id': _hollidays_id,
                                        'date_ini_attendance': _date_ini_attendance,
                                        'date_end_attendance': _date_ini_attendance,
                                        'payslip_id': _paylist,
                                        'contract_id': contract.id,
                                        'state' : _state
                                    }))
                else:
                    _holidays.append((0, 0, {
                                'ini_date_hollidays': _ini_date_hollidays,
                                'fin_date_hollidays': _fin_date_hollidays,
                                'hollidays_id': _hollidays_id,
                                'date_ini_attendance': _date_ini_attendance,
                                'date_end_attendance': _date_ini_attendance,
                                'payslip_id': _paylist,
                                'contract_id': contract.id,
                                'state' : _state
                            }))
                
            contract.write({
                'hollidays_ids' : _holidays
                }) 

    @api.model
    def confg_payroll_cron(self):

        modelo_config_nomina = self.env['hr.config.payroll']
        consulta_config = modelo_config_nomina.search([('fecha_final','>=',fecha_actual)])
        if consulta_config:
            salario_minimo = 0
            auxilio_trans = 0
          
            for data in consulta_config:
                if data.tipo == 'salario_min':
                    salario_minimo = data.valor
                if data.tipo == 'aux_trans':
                    auxilio_trans == data.valor
        
        self.salario_minimo= salario_minimo
        self.aux_transporte = auxilio_trans















        

            

    def configuracion(self):
        salario_minimo = 0
        auxilio_trans = 0
        sub_alimenentacion = 0
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        modelo_config_nomina = self.env['hr.config.payroll']
        consulta_config = modelo_config_nomina.search([('fecha_final','>=',fecha_actual)])
        if consulta_config:
            for data in consulta_config:
                if data.tipo == 'salario_min':
                    salario_minimo = data.valor
                if data.tipo == 'aux_trans':
                    auxilio_trans == data.valor
                if data.tipo == 'sub_alimen':
                    sub_alimenentacion = data.valor

        return sub_alimenentacion, auxilio_trans, salario_minimo
    @api.model
    def default_get(self, vals):   

        result = super(hr_employee_category, self).default_get(vals)
        _config = self.configuracion()  
        result.update({
                'salario_minimo' : _config[2],
                'aux_transporte' : _config[1],
                })
        
        return result

    @api.multi
    @api.onchange('base_sal_min')
    def _on_change_product(self):
        _config = self.configuracion()

        if self.base_sal_min:
            if self.salario_minimo != 0:
                self.wage = self.salario_minimo
            else:
                self.wage = _config[2]
                self.salario_minimo= _config[2]

        
class holidays_record(models.Model):

    _name = 'holidays.record'

    ini_date_hollidays = fields.Date('Desde')
    fin_date_hollidays = fields.Date('Hasta')
    hollidays_id = fields.Many2one('hr.leave', 'Ausencias')
    date_ini_attendance = fields.Date('Desde')
    date_end_attendance = fields.Date('Hasta')
    payslip_id = fields.Many2one('hr.payslip', u'Liquidacion')
    contract_id = fields.Integer('Contrato' ,required = True )
    state = fields.Selection([('pending', 'Pending'), ('programmed', 'Programmed'),
     ('liquidated', 'Liquidated')], 'State', default = 'pending')




   

