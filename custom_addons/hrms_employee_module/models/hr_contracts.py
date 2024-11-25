import logging
import pytz
import threading
from collections import OrderedDict, defaultdict
from datetime import date, datetime, timedelta
from psycopg2 import sql

from odoo import api, fields, models, tools, SUPERUSER_ID
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression
from odoo.tools.translate import _
from odoo.tools import date_utils, email_split, is_html_empty, groupby
from odoo.tools.misc import get_lang
from random import randint
from odoo.exceptions import ValidationError

    
class HR_Contract_Type(models.Model):
    _name = 'hr.contracts.types'
    _description = 'Contract Types'

    active = fields.Boolean('Active', store=True, default=True)
    contract_type = fields.Char('Contract Type', store=True, default=True)
    salary_structure_type = fields.Char('Salary Structure Type', store=True, default=True)
    salary_structure = fields.Char('Salary Structure', store=True, default=True)
    salary_journal = fields.Char('Salary Journal', store=True, default=True)


class HR_Contract(models.Model):
    _name = 'hr.contracts'
    _description = 'Contracts'
    # _rec_name = 'employee_id'

    active = fields.Boolean('Active', store=True, default=True)
    employee_name_id = fields.Many2one('hr.employee.masterlist','Employee Name', store=True)
    employee_id = fields.Char('Employee ID', related='employee_name_id.employee_id', store=True)
    contract_start_date = fields.Date('Contract Start Date', store=True)
    contract_end_date = fields.Date('Contract End Date', store=True)
    notice_period = fields.Integer('Notice Period', store=True, help='Number of days required for notice before termination')
    working_schedule_id = fields.Many2one('resource.calendar','Working Schedule', store=True, readonly=False)
    salary_structure_type = fields.Char('Salary Structure Types', related='contract_type_id.salary_structure_type', store=True, readonly=False)
    department_id = fields.Many2one('hr.departments','Department', store=True, readonly=False)
    salary_structure = fields.Char('Salary Structure', store=True, readonly=False)
    job_position_id = fields.Many2one('hr.job.position','Job Position', store=True, readonly=False)
    contract_type_id = fields.Many2one('hr.contracts.types','Contract Type', store=True, readonly=False)
    wage = fields.Char('Wage', store=True, readonly=False)
    # currency_id = fields.Many2one('res.currency', string="Currency", required=True) 
    note = fields.Text('Note', store=True, readonly=False)
    # salary_journal = fields.Many2one('hr.contracts.type','Salary Journal', related='contract_type_id.salary_journal', store=True, readonly=False)