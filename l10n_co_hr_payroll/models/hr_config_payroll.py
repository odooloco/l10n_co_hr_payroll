# -*- coding: utf-8 -*-
##############################################################################

##############################################################################
import logging
_logger = logging.getLogger(__name__)
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo.osv import osv
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class hr_config_payroll(models.Model):
    _name = 'hr.config.payroll' 
    
    name = fields.Char('Nombre')
    tipo = fields.Selection([('salario_min','Salario Minimo'), ('aux_trans','Auxilio de Transporte'),('sub_alimen', 'Subsidio de Alimentacion')])
    valor = fields.Float('Valor para la Vigencia')
    fecha_inicial = fields.Date('Fecha Inicial de Vigencia')
    fecha_final = fields.Date('Fecha Final de Vigencia')

    @api.one 
    @api.constrains('tipo', 'fecha_inicial', 'fecha_final')
    def _check_confg(self):
        model_config = self.env['hr.config.payroll']
        consult = model_config.search([('tipo','=',self.tipo),('fecha_inicial', '<=', self.fecha_inicial),('fecha_final', '>=', self.fecha_final)])

        if consult:
            if len( consult ) > 1:
                raise ValidationError(_('Ya existe un registro con las mismas caracteristicas que desea guardar por favor verifique la información.'))

