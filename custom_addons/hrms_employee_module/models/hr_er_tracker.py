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


class PMFTracker(models.Model):
    _name = 'hr.er.tracker.pmf'
    _description = 'HR ER Tracker: PMF Tracker'
    _rec_name = 'employee_id'

    active = fields.Boolean('Active', store=True, default=True)
    employee_id = fields.Char('Employee ID' , store=True, related="employee_name_id.employee_id")
    employee_name_id = fields.Many2one('hr.employee.masterlist', string='Employee Name', store=True, compute='_compute_complete_name_id', readonly=False)
    hire_date = fields.Date('Hire Date', store=True, related="employee_name_id.hire_date")
    account_id = fields.Many2one('hr.departments', string='Account', store=True, related="employee_name_id.department_id")
    position = fields.Char('Previous Position', store=True, readonly=False)
    new_position = fields.Char('New Position', store=True)
    current_rate = fields.Char('Current Rate', store=True)
    new_rate = fields.Char('New Rate', store=True)

    @api.onchange('current_rate')
    def _onchange_current_rate(self):
        if self.current_rate:
            self.current_rate = 'PHP {}'.format(self.current_rate)

    @api.onchange('new_rate')
    def _onchange_new_rate(self):
        if self.new_rate:
            self.new_rate = 'PHP {}'.format(self.new_rate)
    effective_date = fields.Date('Effective date', store=True)
    email = fields.Char('Email', store=True, related="employee_name_id.employee_email_address")
    manager_id = fields.Many2one("hr.employee.masterlist", string='Manager', store=True, related="employee_name_id.parent_id")
    # type_of_movement = fields.Selection([('additional_task_and_allowance','Additional Task and Allowance'), ('promotion', 'Promotion'), ('salary_adjustment','Salary Adjustment'), ('job_title_change','Job Title Change'), 
    #                                      ('job_title_change_and_salary_adjustment','Job Title Change and Salary Adjustment'), ('promotion_and_salary_adjustment','Promotion and Salary Adjustment'), ('transfer','Transfer'), 
    #                                      ('lateral_transfer','Lateral Transfer'),('job_title_change_lateral_movement_and_salary_adjustment','Job Title Change, Lateral Movement and Salary Adjustment'), ('promotion_and_exempt_employee', 'Promotion & Exempt Employee'),
    #                                      ('change_in_immediate_superior','Change In Immediate Superior'), ('transfer_and_salary_adjustment','Transfer & Salary Adjustment'), 
    #                                      ('salary_adjustment_and_early_regularization','Salary Adjustment & Early Regularization'), ('pppa_extension', 'PPPA Extension'), 
    #                                      ('lateral_transfer_and_salary_adjustment', 'Lateral Transfer and Salary Adjustment'), 
    #                                      ('reprofile_change_job_title_salary_adjustment','Reprofile, Change Job Title, Salary Adjustment'),
    #                                      ('promotion_and_transition_to_probationary','Promotion and Transition to Probationary'), ('pppa','PPPA'),('classification_change','Classification Change'), 
    #                                      ('early_regularization','Early Regularization'), ('transition_to_probation_status', 'Transition to Probation Status'), 
    #                                      ('project_based_employment_extension', 'Project-based employment extension')],'Type of Movement', store=True)
    c_type_of_movement_id = fields.Many2one('hr.er.tracker.pmf.type.of.movement', string='Type of Movement', store=True, readonly=False)
    pmf_sent_date = fields.Date('PMF Sent Date', store=True)
    hr_representative = fields.Char('HR Representative', store=True)
    remarks = fields.Text('Remarks', store=True)
    
    # Additional Fields
    first_name = fields.Char('First Name', store=True, tracking=True, related="employee_name_id.first_name")
    last_name = fields.Char('Last Name', store=True, tracking=True, related="employee_name_id.last_name")
    middle_name = fields.Char('Middle Name', store=True, tracking=True, related="employee_name_id.middle_name")
    
    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_complete_name_id(self):
        for record in self:
            name_parts = [part for part in [record.first_name, record.middle_name, record.last_name] if part]
            record.employee_name_id = ' '.join(name_parts)

class PMFTracker_type_of_movement(models.Model):
    _name = 'hr.er.tracker.pmf.type.of.movement'
    _description = 'HR ER Tracker: PMF Tracker - Type of Movement'
    _rec_name = 'type_of_movement'

    active = fields.Boolean('Active', store=True, default=True)
    type_of_movement = fields.Char('Type of Movement' , store=True)
    

class DATracker(models.Model):
    _name = 'hr.er.tracker.da'
    _description = 'HR ER Tracker: DA Tracker'
    _rec_name = 'employee_number'

    active = fields.Boolean('Active', store=True, default=True)
    employee_number = fields.Char('Employee Number' , store=True, related="complete_name_id.employee_id")          
    last_name = fields.Char('Last Name', store=True, related="complete_name_id.last_name")
    first_name = fields.Char('First Name', store=True, related="complete_name_id.first_name")
    middle_name = fields.Char('Middle Name', store=True, related="complete_name_id.middle_name")
    complete_name_id = fields.Many2one('hr.employee.masterlist', string='Complete Name', store=True, readonly=False, compute='_compute_complete_name_id')
    hire_date = fields.Date('Hire Date', store=True, related="complete_name_id.hire_date")
    account_id = fields.Many2one('hr.departments', string='Account', store=True, related="complete_name_id.department_id")
    main_infraction = fields.Text('Main Infraction', store=True)
    section = fields.Text('Section', store=True)
    description = fields.Text('Description', store=True)
    ir_received_date = fields.Date('IR Received Date', store=True)
    hr_representative = fields.Char('HR Representative', store=True)
    nte_serve_date = fields.Date('NTE Serve Date', store=True)
    nte_received_date = fields.Date('NTE Received Date', store=True)
    ah_date = fields.Date('AH Date', store=True)
    ah_time = fields.Char('AH Time', store=True)
    c_decision = fields.Selection([('exonerate','Exonerate'), ('written_warning', 'Written Warning'), ('final_written_warning','Final Written Warning'), 
                                   ('termination','Termination'), ('coaching_opportunity','Coaching Opportunity'),   
                                   ('stern_warning','Stern Warning'),('na','N/A')],'Decision', store=True)
    nda_served_date = fields.Date('NDA Served Date', store=True)
    termination_date = fields.Date('Termination Date', store=True)
    remarks = fields.Text('Remarks', store=True)
    level_of_sanction= fields.Selection([('minor', 'Minor'), ('serious', 'Serious'), ('grave', 'Grave')], 'Level of Sanction', store=True)

    @api.onchange('level_of_sanction')
    def onchange_level_of_sanction(self):
        if self.level_of_sanction == 'grave':
            return {'domain': {
                'ah_date': [('ah_date', '!=', False)],
                'ah_time': [('ah_time', '!=', False)],
            }}
        else:
            return {'domain': {
                'ah_date': [('ah_date', '=', False)],
                'ah_time': [('ah_time', '=', False)],
            }}
            
    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_complete_name_id(self):
        for record in self:
            name_parts = [part for part in [record.first_name, record.middle_name, record.last_name] if part]
            record.complete_name_id = ' '.join(name_parts)

class HR_RTWO_Tracker(models.Model):
    _name = 'hr.rtwo.tracker'
    _description = 'RTWO Tracker'
    _rec_name = 'employee_id'

    active = fields.Boolean('Active', store=True, default=True)

    employee_id = fields.Char('Employee ID', store=True, index=True, related="complete_name_id.employee_id")
    last_name = fields.Char('Last Name', store=True, index=True, related="complete_name_id.last_name")
    first_name = fields.Char('First Name', store=True, index=True, related="complete_name_id.first_name")
    middle_name = fields.Char('Middle Name', store=True, index=True, related="complete_name_id.middle_name")
    complete_name_id = fields.Many2one('hr.employee.masterlist', string='Complete Name', store=True, index=True, readonly=False, compute='_compute_complete_name_id')
    hire_date = fields.Date('Hire Date', store=True, index=True, related="complete_name_id.hire_date")
    personal_email_address = fields.Char('Personal Email Address', store=True, index=True, related="complete_name_id.personal_email_address")
    work_email_address = fields.Char('Work Email Address', store=True, index=True, related="complete_name_id.employee_email_address")
    requestor_name = fields.Char('Requestor Name', store=True, index=True)
    hr_representative = fields.Char('HR Representative', store=True, index=True)
    start_date_ncns = fields.Date('Start Date NCNS', store=True, index=True)
    rtwo_letter_sent = fields.Date('RTWO Letter Sent', store=True, index=True)
    first_rtwo_hearing = fields.Date('First RTWO hearing', store=True, index=True)
    first_rtwo_time = fields.Char('Time (1st RTWO)',store=True, index=True)
    second_rtwo = fields.Selection([('yes', 'Yes'), ('no', 'No')], 'Second RTWO?', store=True)

    @api.onchange('second_rtwo')
    def onchange_second_rtwo(self):
        if self.second_rtwo == 'yes':
            return {'domain': {
                'second_rtwo_hearing': [('second_rtwo_hearing', '!=', False)],
                'second_rtwo_time': [('second_rtwo_time', '!=', False)],
            }}
        else:
            return {'domain': {
                'second_rtwo_hearing': [('second_rtwo_hearing', '!=', False)],
                'second_rtwo_time': [('second_rtwo_time', '!=', False)],
            }}
    second_rtwo_hearing = fields.Date('Second RTWO hearing', store=True, index=True)
    second_rtwo_time = fields.Char('Time (2nd RTWO)',store=True, index=True)
    termination_date = fields.Date('Termination Date', store=True, index=True)
    remarks = fields.Text('Remarks', store=True, index=True)
    
    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_complete_name_id(self):
        for record in self:
            name_parts = [part for part in [record.first_name, record.middle_name, record.last_name] if part]
            record.complete_name_id = ' '.join(name_parts)

class HR_Probitionary_Extension_Tracker(models.Model):
    _name = 'hr.probitionary.extension.tracker'
    _description = 'Probitionary Extension Tracker'
    _rec_name = 'employee_id'

    active = fields.Boolean('Active', store=True, default=True)

    employee_id = fields.Char('Employee ID', store=True, index=True, related="complete_name_id.employee_id")
    complete_name_id = fields.Many2one('hr.employee.masterlist', string='Complete Name', store=True, index=True, readonly=False, compute='_compute_complete_name_id')
    hire_date = fields.Date('Hire Date', store=True, index=True, related="complete_name_id.hire_date")
    account_id = fields.Many2one('hr.departments', string='Account', store=True, index=True, related="complete_name_id.department_id")
    position_id = fields.Many2one('hr.job.positions','Position', store=True, index=True, related="complete_name_id.position_id")
    fifth_month_review = fields.Date('5th Month Review', store=True, index=True)
    regularization_date = fields.Date('Regularization Date', store=True, index=True)
    extension_date = fields.Date('Extension Date', store=True, index=True)
    
     # Additional Fields
    first_name = fields.Char('First Name', store=True, tracking=True, related="complete_name_id.first_name")
    last_name = fields.Char('Last Name', store=True, tracking=True, related="complete_name_id.last_name")
    middle_name = fields.Char('Middle Name', store=True, tracking=True, related="complete_name_id.middle_name")
    
    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_complete_name_id(self):
        for record in self:
            name_parts = [part for part in [record.first_name, record.middle_name, record.last_name] if part]
            record.complete_name_id = ' '.join(name_parts)

class HR_PPPA_Tracker(models.Model):
    _name = 'hr.pppa.tracker'
    _description = 'PPPA Tracker'
    _rec_name = 'employee_id'

    active = fields.Boolean('Active', store=True, default=True)

    employee_id = fields.Char('Employee ID', store=True, index=True, related="complete_name_id.employee_id")
    complete_name_id = fields.Many2one('hr.employee.masterlist', string='Complete Name', store=True, index=True, readonly=False, compute='_compute_complete_name_id')
    hire_date = fields.Date('Hire Date', store=True, index=True, related="complete_name_id.hire_date")
    account_id = fields.Many2one('hr.departments', string='Account', store=True, index=True, related="complete_name_id.department_id")
    position = fields.Char('Position', store=True, index=True)
    temporary_position = fields.Char('Temporary position', store=True, index=True)
    allowance = fields.Char('Allowance', store=True, index=True)
    start_date = fields.Date('Start Date', store=True, index=True)
    end_date = fields.Date('End Date', store=True, index=True)
    remarks = fields.Text('Remarks', store=True, index=True)
    
    # Additional Fields
    first_name = fields.Char('First Name', store=True, tracking=True, related="complete_name_id.first_name")
    last_name = fields.Char('Last Name', store=True, tracking=True, related="complete_name_id.last_name")
    middle_name = fields.Char('Middle Name', store=True, tracking=True, related="complete_name_id.middle_name")
    
    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_complete_name_id(self):
        for record in self:
            name_parts = [part for part in [record.first_name, record.middle_name, record.last_name] if part]
            record.complete_name_id = ' '.join(name_parts)

class HR_Project_Based_Extension(models.Model):
    _name = 'hr.project.based.extension'
    _description = 'Project Based Extension'
    _rec_name = 'employee_id'

    active = fields.Boolean('Active', store=True, default=True )

    employee_id = fields.Char('Employee ID', store=True, index=True, related="complete_name_id.employee_id")
    complete_name_id = fields.Many2one('hr.employee.masterlist', string='Complete Name', store=True, index=True, readonly=False, compute='_compute_complete_name_id')
    hire_date = fields.Date('Hire Date', store=True, index=True, related="complete_name_id.hire_date")
    account_id = fields.Many2one('hr.departments', string='Account', store=True, index=True, related="complete_name_id.department_id")
    position_id = fields.Many2one('hr.job.positions','Position', store=True, index=True, related="complete_name_id.position_id")
    original_eoc = fields.Date('Original EOC', store=True, index=True)
    new_eoc = fields.Date('New EOC', store=True, index=True)
    
     # Additional Fields
    first_name = fields.Char('First Name', store=True, tracking=True, related="complete_name_id.first_name")
    last_name = fields.Char('Last Name', store=True, tracking=True, related="complete_name_id.last_name")
    middle_name = fields.Char('Middle Name', store=True, tracking=True, related="complete_name_id.middle_name")
    
    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_complete_name_id(self):
        for record in self:
            name_parts = [part for part in [record.first_name, record.middle_name, record.last_name] if part]
            record.complete_name_id = ' '.join(name_parts)

class HR_PIP_Tracker(models.Model):
    _name = 'hr.pip.tracker'
    _description = 'PIP Tracker'
    _rec_name = 'employee_number'

    active = fields.Boolean('Active', store=True, default=True)

    employee_number = fields.Char('Employee Number', store=True, index=True, related="complete_name_id.employee_id")
    last_name = fields.Char('Last Name', store=True, index=True, related="complete_name_id.last_name")
    first_name = fields.Char('First Name', store=True, index=True, related="complete_name_id.first_name")
    middle_name = fields.Char('Middle Name', store=True, index=True, related="complete_name_id.middle_name")
    complete_name_id = fields.Many2one('hr.employee.masterlist', string='Complete Name', store=True, index=True, readonly=False, compute='_compute_complete_name_id')
    hire_date = fields.Date('Hire Date', store=True, index=True, related="complete_name_id.hire_date")
    account_id = fields.Many2one('hr.departments', string='Account', store=True, index=True, related="complete_name_id.department_id")
    hr_representative = fields.Char('HR Representative', store=True, index=True)
    pip_start_date = fields.Date('PIP Start Date', store=True, index=True)
    pip_1 = fields.Char('PIP 1 (Passed/Failed)', store=True, index=True)
    pip_2 = fields.Char('PIP 2 (Passed/Failed)', store=True, index=True)
    second_pip_1 = fields.Char('2nd PIP 1 (Passed/Failed)', store=True, index=True)
    graduate = fields.Char('Graduate?', store=True, index=True)
    termination_date = fields.Date('Termination Date', store=True, index=True)
    remarks = fields.Text('Remarks', store=True, index=True)
    
    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_complete_name_id(self):
        for record in self:
            name_parts = [part for part in [record.first_name, record.middle_name, record.last_name] if part]
            record.complete_name_id = ' '.join(name_parts)
