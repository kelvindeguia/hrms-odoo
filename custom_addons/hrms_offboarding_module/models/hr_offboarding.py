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

class HR_OffBoarding(models.Model):
    _name = 'hr.offboarding'
    _description = 'HR Offboarding Module'
    _rec_name = 'employee_id'
    
    _inherit = ['hr.employee.masterlist', 'hr.departments','hr.job.positions','mail.thread', 'mail.activity.mixin']


    active = fields.Boolean('Active', store=True, default=True)
    employee_id = fields.Char('Employee ID', store=True, related="employee_name_id.employee_id")
    # Employee ID VALIDATION ERROR
    @api.constrains('employee_id')
    def _check_duplicate(self):
        for record in self:
            # Check if there are other records with the same employee_id
            if record.employee_id:
                duplicate_records = self.search([('employee_id', '=', record.employee_id), ('id', '!=', record.id)])
                if duplicate_records:
                    raise ValidationError('Employee Id already exists.')    
                  
    employee_name_id = fields.Many2one('hr.employee.masterlist',string='Employee Name', store=True, readonly=False, compute='_compute_complete_name')
    account_id = fields.Many2one('hr.departments', string='Account', store=True, related="employee_name_id.department_id")
    hire_date = fields.Date('Hire Date', store=True, related="employee_name_id.hire_date")
    last_working_date = fields.Char('Last Working Date', store=True)
    seperation_date = fields.Date('Separation Date', store=True)
    c_company = fields.Selection([('isupport_worldwide', 'iSupport Worldwide'), ('iswerk', 'ISWerk')],'Company', store=True)
    overall_clearance_status = fields.Char('Overall Clearance Status', store=True)
    hr_remarks = fields.Text('HR Remarks', store=True)
    disabling_of_it_access = fields.Char('Disabling of IT Access', store=True)
    odoo_access_disabling = fields.Char('Odoo Access Disabling', store=True)
    assets_pullout_status = fields.Char('Asset Pull Out Status(Assets Deployed Onsite)', store=True)
    it_assets_returned = fields.Char('IT Assets Returned?', store=True)
    pending_it_assets_to_be_returned = fields.Char('Pending IT Assets to be Returned', store=True)
    it_clearance_status = fields.Char('IT Clearance Status', store=True)
    it_remarks = fields.Text('IT Remarks', store=True)
    locker_facilities = fields.Char('Locker Key', store=True)
    pedestal_key = fields.Char('Pedestal Key', store=True)
    accesories = fields.Char('Accessories', store=True)
    facilities_clearance_status = fields.Char('Facilities Clearance Status', store=True)
    facilities_remarks = fields.Text('Facilities Remarks', store=True)
    created = fields.Datetime('Created', store=True)
    item_type = fields.Char('Item Type', store=True)
    path = fields.Char('Path', store=True)
    
    # Additional Fields
    first_name = fields.Char('First Name', store=True, tracking=True, related="employee_name_id.first_name")
    last_name = fields.Char('Last Name', store=True, tracking=True, related="employee_name_id.last_name")
    middle_name = fields.Char('Middle Name', store=True, tracking=True, related="employee_name_id.middle_name")
    
    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_complete_name(self):
        for record in self:
            name_parts = [part for part in [record.first_name, record.middle_name, record.last_name] if part]
            record.employee_name_id = ' '.join(name_parts)