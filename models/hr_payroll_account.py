#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# from odoo import api
import babel
import time
from odoo import models, fields, api, _
from odoo import netsvc
from datetime import date, datetime, time, timedelta
from pytz import timezone
from odoo import api, tools
from odoo.osv import osv
# from odoo.tools import config, float_compare
from odoo.tools import config, float_compare, float_is_zero
from odoo.tools.translate import _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class hr_salary_rule(osv.osv):
    _inherit = 'hr.salary.rule'
    
    origin_partner = fields.Selection((('employee','Empleado'),
                                            ('eps','EPS'),
                                            ('fp','Fondo de Pensiones'),
                                            ('fc','Fondo de cesantías'),
                                            ('rule','Regla salarial')),
                                  'Tipo de tercero', required=True, default = 'employee')
    partner_id = fields.Many2one('res.partner', 'Tercero')
    

hr_salary_rule()

class hr_payslip(osv.osv):
    '''
    Pay Slip
    '''
    _inherit = 'hr.payslip'
    _description = 'Pay Slip'

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        employee_id = self.employee_id
        date_from = self.date_from
        date_to = self.date_to

        #ttyme = datetime.fromtimestamp(time.mktime(time.strptime(date_from.decode('ascii'), "%Y-%m-%d")))
        #self.name = _('Salary Slip of %s for %s') % (employee_id.name, tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=self.env.context.get('lang', 'en_US'))))
        self.company_id = employee_id.company_id

        if not self.env.context.get('contract') or not self.contract_id:
            
            contract_ids = self.get_contract(employee_id, date_from, date_to)
            
            if not contract_ids:
                return
            self.contract_id = self.contract_id.browse(contract_ids[0])

        if not self.contract_id.struct_id:
            return
        self.struct_id = self.contract_id.struct_id

        #computation of the salary input
        worked_days_line_ids = self.get_worked_day_lines(self.contract_id, date_from, date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines
        input_line_ids = self.get_inputs(self.contract_id, date_from, date_to)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        return

    def process_sheet(self, cr, uid, ids, context=None):
        move_pool = self.pool.get('account.move')
        hr_payslip_line_pool = self.pool['hr.payslip.line']
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Payroll')

        for slip in self.browse(cr, uid, ids, context=context):
            line_ids = []
            debit_sum = 0.0
            credit_sum = 0.0
            date = slip.date or slip.date_to

            partner_eps_id = slip.employee_id.eps_id.id
            partner_fp_id = slip.employee_id.fp_id.id
            partner_fc_id = slip.employee_id.fc_id.id

            default_partner_id = slip.employee_id.address_home_id.id

            name = _('Payslip of %s') % (slip.employee_id.name)
            move = {
                'narration': name,
                'ref': slip.number,
                'journal_id': slip.journal_id.id,
                'date': date,
            }
            for line in slip.details_by_salary_rule_category:
                amt = slip.credit_note and -line.total or line.total
                if float_is_zero(amt, precision_digits=precision):
                    continue

                partner_id = line.salary_rule_id.register_id.partner_id and line.salary_rule_id.register_id.partner_id.id or default_partner_id

                debit_account_id = line.salary_rule_id.account_debit.id
                credit_account_id = line.salary_rule_id.account_credit.id

                if line.salary_rule_id.origin_partner == 'employee':
                    partner_id = default_partner_id
                elif line.salary_rule_id.origin_partner == 'eps':
                    partner_id = partner_eps_id
                elif line.salary_rule_id.origin_partner == 'fp':
                    partner_id = partner_fp_id
                elif line.salary_rule_id.origin_partner == 'fc':
                    partner_id = partner_fc_id
                elif line.salary_rule_id.origin_partner == 'rule':
                    partner_id = line.salary_rule_id.partner_id.id
                else:
                    partner_id = default_partner_id

                if debit_account_id:
                    debit_line = (0, 0, {
                        'name': line.name,
                        # 'partner_id': hr_payslip_line_pool._get_partner_id(cr, uid, line, credit_account=False, context=context),
                        'partner_id': partner_id,
                        'account_id': debit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amt > 0.0 and amt or 0.0,
                        'credit': amt < 0.0 and -amt or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id and line.salary_rule_id.analytic_account_id.id or False,
                        'tax_line_id': line.salary_rule_id.account_tax_id and line.salary_rule_id.account_tax_id.id or False,
                    })
                    line_ids.append(debit_line)
                    debit_sum += debit_line[2]['debit'] - debit_line[2]['credit']

                if credit_account_id:
                    credit_line = (0, 0, {
                        'name': line.name,
                        # 'partner_id': hr_payslip_line_pool._get_partner_id(cr, uid, line, credit_account=True, context=context),
                        'partner_id': partner_id,
                        'account_id': credit_account_id,
                        'journal_id': slip.journal_id.id,
                        'date': date,
                        'debit': amt < 0.0 and -amt or 0.0,
                        'credit': amt > 0.0 and amt or 0.0,
                        'analytic_account_id': line.salary_rule_id.analytic_account_id and line.salary_rule_id.analytic_account_id.id or False,
                        'tax_line_id': line.salary_rule_id.account_tax_id and line.salary_rule_id.account_tax_id.id or False,
                    })
                    line_ids.append(credit_line)
                    credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

            if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:
                acc_id = slip.journal_id.default_credit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Credit Account!') % (slip.journal_id.name))
                adjust_credit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': 0.0,
                    'credit': debit_sum - credit_sum,
                })
                line_ids.append(adjust_credit)

            elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                acc_id = slip.journal_id.default_debit_account_id.id
                if not acc_id:
                    raise UserError(_('The Expense Journal "%s" has not properly configured the Debit Account!') % (slip.journal_id.name))
                adjust_debit = (0, 0, {
                    'name': _('Adjustment Entry'),
                    'partner_id': False,
                    'account_id': acc_id,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                    'debit': credit_sum - debit_sum,
                    'credit': 0.0,
                })
                line_ids.append(adjust_debit)

            move.update({'line_ids': line_ids})
            move_id = move_pool.create(cr, uid, move, context=context)
            self.write(cr, uid, [slip.id], {'move_id': move_id, 'date' : date, 'state': 'done', 'paid': True}, context=context)
            move_pool.post(cr, uid, [move_id], context=context)
        return True

    
    def get_worked_day_lines(self,contract_ids, date_from, date_to):
        
        #@param contract_ids: list of contract id
        #@return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        
        #value = {}
        ##payslip = self.pool.get('hr.payslip')
        #model_hr_contract = self.env['hr.contract']
        def was_on_leave(employee_id, datetime_day):
            res = False
            res2 = []

            holiday_ids  = []                

            for hour in range( 0, 24 ):

                day = datetime_day.strftime("%Y-%m-%d " + str( hour ) + ":00:00") 

                sql = """
                select id as id from hr_leave
                where state = 'validate' and employee_id = %s 
                and (date_from - interval '5 hour') <= '%s' and (date_to  - interval '5 hour') >= '%s'

                """ % ( employee_id, day, day )

                self.env.cr.execute( sql )
                res = self.env.cr.dictfetchall(  )


                holiday_ids += [ re.get('id') for re in res ]


            if holiday_ids:
                res = self.env['hr.leave'].browse(holiday_ids)[0]


            return res

        res = []

        for contract in contract_ids:
            if not contract.resource_calendar_id:
                #fill only if the contract as a working schedule linked
                continue
            attendances = {
                 'name': _("Normal Working Days paid at 100%"),
                 'sequence': 1,
                 'code': 'WORK100',
                 'number_of_days': 0.0,
                 'number_of_hours': 0.0,
                 'contract_id': contract.id,
            }
            leaves = {}
            day_from = datetime.combine(fields.Date.from_string(date_from), time.min)
            day_to = datetime.combine(fields.Date.from_string(date_to), time.max)


            if day_to.day == 31:
                nb_of_days = ((day_to - day_from).days + 1) -1

            elif day_to.day == 28 and day_to.month==2: 
                nb_of_days = ((day_to - day_from).days + 3)

            elif day_to.day == 29 and day_to.month==2: 
                nb_of_days = ((day_to - day_from).days + 1) + 1

            else:
                nb_of_days = (day_to - day_from).days + 1
          
            in_id = []
            ignore_days = {}
            for day in range(0, nb_of_days):
                if contract.date_end:
                    contract_date = contract.date_end
                else:
                    contract_date = str(day_from.year)+'-12-32' 
                      
                if str(day_from + timedelta(days=day)) <= contract_date  and (str(day_from + timedelta(days=day)) >= str(contract.date_start)):
                    calendar = contract.resource_calendar_id
                    tz = timezone(calendar.tz)
                    working_hours_on_day = calendar.get_work_hours_count(
                        tz.localize(day_from),
                        tz.localize(day_to),
                        compute_leaves=False,
                    )
                    if working_hours_on_day:
                       
                        #the employee had to work
                        leave_type = was_on_leave(contract.employee_id.id, day_from + timedelta(days=day))

                        if leave_type:

                            if leave_type.number_of_days >= 1:

                                
                                ignore_days.update({
                                    leave_type.id : ignore_days.get( leave_type.id, 0 ) + 1 
                                })
                        
                                if ignore_days.get( leave_type.id, 0 ) > leave_type.number_of_days:
                                    attendances['number_of_days'] += 1.0
                                    continue

                            
                            if leave_type.holiday_status_id.categ_id.notunaffected_days:
                                if leave_type.holiday_status_id.categ_id.is_hours_additional:
                                    if leave_type.name in leaves:
                                       
                                        if leave_type.id in in_id:
                                           
                                            attendances['number_of_days'] += 1.0
                                            attendances['number_of_hours'] += working_hours_on_day
                                            leaves[leave_type.name]['number_of_days'] += 1.0
                                            continue

                                        in_id.append( leave_type.id )
                                   
                                        attendances['number_of_days'] += 1.0
                                        attendances['number_of_hours'] += working_hours_on_day
                                    else:
                                        
                                        leaves[leave_type.name] = {
                                            'name': leave_type.name,
                                            'sequence': 0,
                                            'code': leave_type.holiday_status_id.name,
                                            'number_of_days': leave_type.number_of_days,
                                            'number_of_hours': leave_type.number_of_hours_temp,
                                            'contract_id': contract.id,
                                        }
                                        in_id.append(leave_type.id )
                                        attendances['number_of_days'] += 1.0
                                        attendances['number_of_hours'] += working_hours_on_day
                                else:
                                    if leave_type.name in leaves:
                                       
                                        leaves[leave_type.name]['number_of_days'] += 1
                                        attendances['number_of_days'] += 1.0
                                        attendances['number_of_hours'] += working_hours_on_day
                                    else:
                                        leaves[leave_type.name] = {
                                            'name': leave_type.name,
                                            'sequence': 0,
                                            'code': leave_type.holiday_status_id.name,
                                            'number_of_days': 1,
                                            'number_of_hours': leave_type.number_of_hours_temp,
                                            'contract_id': contract.id,
                                        }
                                        
                                        attendances['number_of_days'] += 1.0
                                        attendances['number_of_hours'] += working_hours_on_day
                            else:
                                
                                if leave_type.name in leaves:
                                    
                                    leaves[leave_type.name]['number_of_days'] += 1
                                   
                                else:
                                    
                                    leaves[leave_type.name] = {
                                        'name': leave_type.name,
                                        'sequence': 5,
                                        'code': leave_type.holiday_status_id.name,
                                        'number_of_days': 1,
                                        'number_of_hours': working_hours_on_day,
                                        'contract_id': contract.id,
                                    }
                                    
                        else:
                            
                            #add the input vals to tmp (increment if existing)
                            attendances['number_of_days'] += 1.0
                            attendances['number_of_hours'] += working_hours_on_day

            leaves = [value for key,value in leaves.items()]
            res += [attendances] + leaves

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
