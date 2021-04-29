# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.osv import osv
from odoo.tools.translate import _
import odoo.addons.decimal_precision as dp

# Agrega campos EPS y Fondo de Pensiones en datos del empleado.

class hr_employee_co(osv.osv):
    _inherit = 'hr.employee'

    eps_id = fields.Many2one('res.partner', 'EPS')
    fp_id = fields.Many2one('res.partner', 'Fondo de Pensiones')
    fc_id =fields.Many2one('res.partner', 'Fondo de Cesantías')

