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
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

class Resignation_Tracker(models.Model):
    _name = 'hr.resignation'
    _description = 'Resignation Tracker'
    _rec_name = 'eid'
    
    _inherit = ['hr.employee.masterlist', 'hr.departments','hr.job.positions','mail.thread', 'mail.activity.mixin']

    active = fields.Boolean('Active', store=True, default=True)
    eid = fields.Char('EID' , store=True, related='full_name_id.employee_id')
     # Employee ID VALIDATION ERROR
    @api.constrains('eid')
    def _check_duplicate(self):
        for record in self:
            # Check if there are other records with the same employee_id
            if record.eid:
                duplicate_records = self.search([('eid', '=', record.eid), ('id', '!=', record.id)])
                if duplicate_records:
                    raise ValidationError('Employee Id already exists.')          
    
    first_name = fields.Char('First Name', store=True, related='full_name_id.first_name')
    last_name = fields.Char('Last Name', store=True, related='full_name_id.last_name')
    middle_name = fields.Char('Middle Name', store=True)            
    full_name_id = fields.Many2one('hr.employee.masterlist',string='Complete Name', store=True, readonly=False, tracking=True)

    # 1st "Department" field change to "Department/Account" to avoid conflict with the last "DEPARTMENT"
    department_account_id = fields.Many2one('hr.departments', string='Account', store=True, related='full_name_id.department_id')
    position_id  = fields.Many2one('hr.job.positions','Job Position', store=True, related='full_name_id.position_id')
    employment_status = fields.Selection([('', ''),('probationary', 'Probationary'), ('regular', 'Regular'), ('project_based', 'Project-Based')],'Employment Status', store=True, related='full_name_id.c_employment_status')
    date_hired = fields.Date('Hire Date', store=True, related='full_name_id.hire_date')
    separation_date = fields.Date('Separation Date', store=True, tracking=True)
    separation_status = fields.Selection([('deceased', 'Deceased'), ('end_of_project', 'END OF PROJECT'), ('non_regularization', 'NON-REGULARIZATION'), ('redundate','REDUNDATE'), ('resigned', 'RESIGNED'), ('retrenched', 'RETRENCHED'), ('terminated', 'TERMINATED')],'Separation Status', store=True, tracking=True)
    category = fields.Selection([('desired', 'Desired'), ('undesired','Undesired'), ('authorized','Authorized')],'Category', store=True, tracking=True)
    eligible_for_rehire = fields.Selection([('yes', 'Yes'), ('no','No'), ('not_cleared','Not Cleared')],'Eligible for rehire?', store=True, tracking=True)
    voluntary_involuntary = fields.Selection([('voluntary', 'Voluntary'), ('involuntary','Involuntary')], 'Voluntary/Involuntary', store=True, tracking=True)
    reason_for_seperation = fields.Selection([('personal_reason_undefined', 'Personal Reason/ Undefined'), ('career_growth_role_expansion', 'Career Growth/Role Expansion'), 
                                                ('redundancy', 'Redundancy'), ('performance','Performance'), ('better_compensation_package', 'Better Compensation Package'), 
                                                ('health_reason', 'Health Reason'), ('resigned_in_liue_of_termination_violation', 'RESIGNED in lieu of termination (violation)'), 
                                                ('resigned_in_liue_of_possible_termination_awol', 'RESIGNED in lieu of possible termination (AWOL)'), ('resigned_in_liue_of_termination_non_regularization', 'RESIGNED in lieu of termination (non-regularization)'),
                                                ('end_of_project', 'End Of Project') , ('family_matters', 'Family Matters'), ('not_satisfied-with_type_of_work_account_processes', 'Not Satisfied with type of work/ account/process'), 
                                                ('change_of_career', 'Change Of Career') , ('termination_violation', 'Termination-Violation') , ('permanent_wfh_set_up', 'Permanent WFH set up') , ('relocation', 'Relocation'), 
                                                ('permanent_day_shift_schedule', 'Permanent Day Shift Schedule') , ('deceased', 'Deceased') , ('job_abandonment', 'Job Abandonment') , ('rto_concerns', 'RTO Concerns'), 
                                                ('career_growth', 'Career Growth'), ('termination_due_to_ncns', 'Termination Due to NCNS'), ('transfer_to_satellite_office', 'Transfer to Satellite Office'), 
                                                ('bda_redundancy', 'BDA Redundancy') , ('pursue_further_studies', 'Pursue further Studies'), ('transportation_concerns', 'Transportation Concerns'),
                                                ('authorized_separation_due_to_sickness', 'Authorized Separation due to Sickness')],'Reason For Separation (Resignation Letter/ Termination Notice)', store=True, tracking=True)
    resignation_letter_recieved = fields.Selection([('yes', 'Yes'), ('no','No'), ('na','N/A')],'Resignation letter recieved', store=True, tracking=True)
    note = fields.Text('Note', store=True)
    # retention_call = fields.Text('Retention Call', store=True)
    exit_interview_reason_for_leaving = fields.Text('Exit Interview Reason for Leaving (Retention Talk)', store=True)
    rl_recieved_date = fields.Date('RL Recieved Date', store=True)
    entity = fields.Selection([('isupport_worldwide', 'iSupport Worldwide'), ('iswerk','ISWerk')],'Entity', store=True, related='full_name_id.company')
    for_final_pay = fields.Char('For final pay (Clearance)', store=True)
    recieved_employment_verification_from = fields.Char('Recieved Employment Verification From?', store=True, tracking=True)
    department = fields.Selection([('',''), ('operation', 'OPERATIONS'), ('support','SUPPORT')],'Department', store=True)
    personal_email = fields.Char('Personal Email Address', store=True, related='full_name_id.personal_email_address')
    tenure_bracket = fields.Char('Tenure Bracket', store=True, compute='_compute_tenure_bracket')
    total_days = fields.Char('Total Days', store=True, compute='_compute_tenure_bracket')
    total_years = fields.Char('Total Years', store=True, compute='_compute_tenure_bracket')
    total_months = fields.Char('Total Months', store=True, compute='_compute_tenure_bracket')
    resignation_status = fields.Selection([('draft','Draft'),('confirm','For Approval'),('approved','Approved'),('rejected','Rejected'),('retract','Retract')],'Resignation Status',default='draft', store=True, tracking=True)

    is_approver = fields.Boolean(string="Is Approver", compute='_compute_is_approver')
    def _compute_is_approver(self):
        for record in self:
            record.is_approver = self.env.user.has_group('hrms_resignation_module.group_hrms_resignation_approver')
            
    def action_approve(self):
        if self.env.user.has_group('hrms_resignation_module.group_hrms_resignation_approver'):
            self.resignation_status = 'approved'
        else:
            raise UserError('You do not have the permissions to approve this record.')
        
    def action_reject(self):
        if self.env.user.has_group('hrms_resignation_module.group_hrms_resignation_approver'):
            self.resignation_status = 'rejected'
        else:
            raise UserError('You do not have the permissions to reject this record.')
    
    @api.depends('date_hired', 'separation_date')
    def _compute_tenure_bracket(self):
        for record in self:
            date_hired = record.date_hired
            separation_date = record.separation_date or fields.Date.today()

            if not date_hired or not separation_date:
                record.tenure_bracket = "N/A"
                record.total_days = "0 Days"
                record.total_years = "0 Years"
                record.total_months = "0 Months"
                continue

            delta = relativedelta(separation_date, date_hired)
            total_days = (separation_date - date_hired).days
            total_years = delta.years
            total_months = delta.years * 12 + delta.months

            # Set fields
            record.total_days = "{} Days".format(total_days)
            record.total_years = "{} Years".format(total_years)
            record.total_months = "{} Months".format(total_months)

            if total_days < 30:
                record.tenure_bracket = "0-30 Days"
            elif 31 <= total_days < 90:
                record.tenure_bracket = "31-90 Days"
            elif 91 <= total_days < 180:
                record.tenure_bracket = "91-180 Days"
            elif 181 <= total_days < 365:
                record.tenure_bracket = "6 Months - 1 Year"
            elif 366 <= total_days < 730:
                record.tenure_bracket = "1-2 Years"
            elif 731 <= total_days < 1460:
                record.tenure_bracket = "2-4 Years"
            else:
                record.tenure_bracket = "More than 4 years"
    
    def button_confirm(self):
       self.write({
           'resignation_status': "confirm"
       })
       
    def button_approved(self):
       self.write({
           'resignation_status': "approved"
       })
    def button_rejected(self):
       self.write({
           'resignation_status': "rejected"
       })
    
    def button_retract(self):
       self.write({
           'resignation_status': "retract"
       })
       
    def button_reset_status(self):
       self.write({
           'resignation_status': "draft"
       })
       
    # secondary_formatted_phone_number = fields.Char('Secondary Phone Number', store=True, readonly=False, related='full_name_id.secondary_formatted_phone_number')

    # @api.constrains('phone_number')
    # def _check_phone_number_length(self):
    #     for record in self:
    #         if record.phone_number and len(record.phone_number) != 13:
    #             raise ValidationError("Formatted phone number must be 11 characters.")

    # @api.onchange('phone_number')
    # def _compute_formatted_phone_number(self):
    #     for record in self:
    #         if record.phone_number and isinstance(record.phone_number, str) and record.phone_number.isdigit():
    #             formatted_number = f"{record.phone_number[:3]}-{record.phone_number[3:6]}-{record.phone_number[6:]}"
                
    #             # Check if the phone number starts with '0' before adding it
    #             if not formatted_number.startswith('0'):
    #                 formatted_number = '0' + formatted_number
                
    #             record.phone_number = formatted_number
    #         else:
    #             # Handle non-numeric phone numbers or empty values
    #             record.phone_number = record.phone_number

    # @api.onchange('secondary_formatted_phone_number')
    # def _compute_secondary_formatted_phone_number(self):
    #     for record in self:
    #         if record.secondary_formatted_phone_number == "N/A":
    #             # Handle "N/A" case
    #             pass
    #         else:
    #             if record.secondary_formatted_phone_number and isinstance(record.secondary_formatted_phone_number, str) and record.secondary_formatted_phone_number.isdigit():
    #                 formatted_number = f"{record.secondary_formatted_phone_number[:3]}-{record.secondary_formatted_phone_number[3:6]}-{record.secondary_formatted_phone_number[6:]}"
                    
    #                 # Check if the phone number starts with '0' before adding it
    #                 if not formatted_number.startswith('0'):
    #                     formatted_number = '0' + formatted_number
                    
    #                 record.secondary_formatted_phone_number = formatted_number
    #             else:
    #                 # Handle non-numeric phone numbers or empty values
    #                 record.secondary_formatted_phone_number = record.secondary_formatted_phone_number
