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


class HR_Performance_Review_Tracker(models.Model):
    _name = 'hr.performance.review.tracker'
    _description = 'HR Performance Review Tracker'
    _rec_name = 'employee_number'

    active = fields.Boolean('Active', store=True, index=True, default=True)

    employee_number = fields.Char('Employee Number', store=True, index=True, related="complete_name_id.employee_id")
    # Employee ID VALIDATION ERROR
    @api.constrains('employee_number')
    def _check_duplicate(self):
        for record in self:
            # Check if there are other records with the same employee_id
            if record.employee_number:
                duplicate_records = self.search([('employee_number', '=', record.employee_number), ('id', '!=', record.id)])
                if duplicate_records:
                    raise ValidationError('Employee Number already exists.')  
                
    complete_name_id = fields.Many2one('hr.employee.masterlist',string='Complete Name', store=True, index=True, readonly=False, compute='_compute_complete_name_id')
    hire_date = fields.Date('Hire Date', store=True, index=True, related="complete_name_id.hire_date")
    c_employment_status = fields.Selection([('', ''),('probationary', 'Probationary'), ('regular', 'Regular'), ('project_based', 'Project-Based'), ('inactive', 'Inactive')],'Employment Status', store=True, index=True)
    # entity = fields.Char('Entity', store=True, index=True, readonly=False)
    c_entity = fields.Selection([('isupport_worldwide', 'iSupport Worldwide'), ('iswerk', 'ISWerk')],'Entity', store=True, index=True)
    department = fields.Selection([('', ''),('operations', 'OPERATIONS'),('support', 'SUPPORT')],'Department', store=True, index=True)
    account_id = fields.Many2one('hr.departments', string='Account', store=True, index=True, related="complete_name_id.department_id")
    position_id = fields.Many2one('hr.job.positions','Position', store=True, index=True, related="complete_name_id.position_id")
    email_address = fields.Char('Email Address', store=True, index=True, related="complete_name_id.employee_email_address")

    # Performance Review POC
    performance_review_poc_name = fields.Char('Performance Review POC Name', store=True, index=True)
    performance_review_poc_email_address = fields.Char('Performance Review POC Email Address', store=True, index=True)

    # Performance Review
    comments = fields.Text('Comments', store=True, index=True)

    third_month_review_date = fields.Date('3rd Month Review Date', store=True, index=True)
    third_month_review_accomplished_date = fields.Date('3rd Month Review Accomplished Date', store=True, index=True)

    fifth_month_review_date = fields.Date('5th Month Review Date', store=True, index=True)
    fifth_month_review_accomplished_date = fields.Date('5th Month Review Accomplished Date', store=True, index=True)

    twentyfour_annual_review_date = fields.Date('2024 Annual Review Date', store=True, index=True)
    twentyfour_annual_review_accomplished_date = fields.Date('2024 Annual Review Accomplished Date', store=True, index=True)

    twentyfive_annual_review_date = fields.Date('2025 Annual Review Date', store=True, index=True)
    twentyfive_annual_review_accomplished_date = fields.Date('2025 Annual Review Accomplished Date', store=True, index=True)

    # Additional Fields
    first_name = fields.Char('First Name', store=True, tracking=True, related="complete_name_id.first_name")
    last_name = fields.Char('Last Name', store=True, tracking=True, related="complete_name_id.last_name")
    middle_name = fields.Char('Middle Name', store=True, tracking=True, related="complete_name_id.middle_name")
    
    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_complete_name_id(self):
        for record in self:
            name_parts = [part for part in [record.first_name, record.middle_name, record.last_name] if part]
            record.complete_name_id = ' '.join(name_parts)