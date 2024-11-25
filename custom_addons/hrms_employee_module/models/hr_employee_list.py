import base64
import logging
import pytz
import threading
from pytz import timezone, UTC
from collections import OrderedDict, defaultdict
from datetime import date, datetime, timedelta
from psycopg2 import sql
from random import choice
from string import digits
from werkzeug.urls import url_encode
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, SUPERUSER_ID
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression
from odoo.tools.translate import _
from odoo.tools import date_utils, email_split, is_html_empty, groupby
from odoo.tools.misc import get_lang
from random import randint
from odoo.exceptions import ValidationError

class HR_Employee_Masterlist(models.Model):
    _name = 'hr.employee.masterlist'
    _description = 'HR Employee Masterlist'
    _rec_name = 'complete_name'
    _inherit = [ 'mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'

    active = fields.Boolean('Active', default=True, store=True)
    # tags = fields.Many2many('hr.tags',string="Status", store=True)
    # @api.constrains('tags')
    # def _check_tags_limit(self):
    #     for record in self:
    #         if len(record.tags) > 1:
    #             raise ValidationError("Only one status can be selected.")
    user_id = fields.Many2one('res.users', string='Related User', store=True)
    
    obt_number = fields.Char('OBT Number', store=True, tracking=True)
    employee_id = fields.Char('Employee ID', store=True, tracking=True)
    # Employee ID VALIDATION ERROR
    @api.constrains('employee_id', 'obt_number')
    def _check_duplicate(self):
        for record in self:
            # Check if there are other records with the same Employee ID and OBT Number
            if record.employee_id:
                duplicate_records = self.search([('employee_id', '=', record.employee_id), ('id', '!=', record.id)])
                if duplicate_records:
                    raise ValidationError('Employee Id already exists.')
                  
            if record.obt_number:
                duplicate_records = self.search([('obt_number', '=', record.obt_number), ('id', '!=', record.id)])
                if duplicate_records:
                    raise ValidationError('OBT Number already exists.')     
                
    first_name = fields.Char('First Name', store=True, readonly=False, required=True, tracking=True)
    last_name = fields.Char('Last Name', store=True, readonly=False, required=True, tracking=True)
    middle_name = fields.Char('Middle Name', store=True, readonly=False, tracking=True)
    complete_name = fields.Char(string='Complete Name', compute='_compute_complete_name', store=True, track_visibilty='onchange')
    start_date = fields.Date('Start Date', store=True, readonly=False, tracking=True)
    date_of_birth = fields.Date('Date of Birth', store=True)
    department_id = fields.Many2one('hr.departments','Department', store=True, index=True, tracking=True)
    position_id = fields.Many2one('hr.job.positions','Job Position', store=True, tracking=True)
    lob = fields.Char('LOB', store=True)
    employee_address = fields.Text('Home Address', store=True)
    city = fields.Char('City', store=True)
    region = fields.Char('Region', store=True)
    personal_email_address = fields.Char('Personal Email Address', store=True, readonly=False)
    employee_email_address = fields.Char('Employee Email Address', store=True, readonly=False)
    mobile_number = fields.Char('Primary Mobile Number', store=True, readonly=False, compute='_compute_formatted_phone_number')
    secondary_formatted_phone_number = fields.Char('Secondary Phone Number', store=True, readonly=False)
    landline_number = fields.Char('Landline Number', store=True, readonly=False)
    
    # 2nd lob optional
    second_lob = fields.Char('LOB', store=True)

    payroll_approver_id = fields.Many2one("hr.employee.masterlist", string='Payroll Approver', store=True, tracking=True)
    payroll_approvers_email_address = fields.Char('Payroll Approvers Email Address', store=True, related="payroll_approver_id.employee_email_address")
    parent_id = fields.Many2one("hr.employee.masterlist", string = 'Manager Name', store=True, tracking=True)# managers_email_address = fields.Char('Managers Email Address', store=True)
    coach_id = fields.Many2one("hr.employee.masterlist", store=True)
    child_ids = fields.One2many("hr.employee.masterlist", 'parent_id', store=True)
    # managers_name = fields.Char('Managers Name', store=True)
    managers_email_address = fields.Char('Managers Email Address', related="parent_id.employee_email_address", store=True)
    performance_review_poc = fields.Char('Performance Review POC', store=True)
    internet_provider = fields.Char('Internet Provider', store=True)
    company = fields.Selection([('isupport_worldwide', 'iSupport Worldwide'), ('iswerk','ISWerk')], 'Company', store=True, readonly=False)
    entity_updated = fields.Date('Entity Updated', store=True)
    all_employees_except_pmi = fields.Char('All Employees except PMI', store=True)
    isupport_employees_distro = fields.Char('iSupport Employees Distro', store=True)
    iswerk_employees_distro = fields.Char('iSWerk Employees Distro', store=True)
    all_sanmar = fields.Char('All Sanmar', store=True)
    all_ammex = fields.Char('All Ammex', store=True)
    lighthouse = fields.Char('LightHouse', store=True)
    isupporthub = fields.Char('iSupportHub', store=True)
    status = fields.Selection([('onboarding','Onboarding'),('active','Active'),('offboarding','Offboarding'),('inactive','Inactive'),('fall_out','Fall Out'),('tbd','TBD')],'Status', tracking=True, readonly=False, default='onboarding', copy=False, store=True)
    def button_fall_out(self):
       self.write({
           'status': "fall_out"
       })
       
    def button_tbd(self):
       self.write({
           'status': "tbd"
       })
    
    def button_active(self):
       self.write({
           'status': "active"
       })
       
    def button_inactive(self):
       self.write({
           'status': "inactive"
       })
       
    def button_offboarding(self):
       self.write({
           'status': "offboarding"
       })
       
    def button_reset_status(self):
       self.write({
           'status': "onboarding"
       })
    
    
    # Added Fields
    # category_ids = fields.Many2many(
    # 'hr.employee.category', 
    # 'employee_masterlist_active_category_rel',  # Different relation table name
    # 'employee_id', 'category_id', 
    # string='Active Employee Categories')
    # department_id = fields.Many2one('hr.department', 'Department', check_company=True, tracking=True)
    # company_id = fields.Many2one('res.company', 'Company', required=True) 
    
    
    family_dependency = fields.Many2many('hr.dependency', string='Family', store=True)
    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", copy=False)
    
    
    request_id = fields.Char('Req ID', store=True, required=False, tracking=True)
    job_offer_date = fields.Date('Job Offer Date', store=True, required=False)
    hire_date = fields.Date('Hire Date', store=True, readonly=False, tracking=True)
    recruiter = fields.Char('Recruiter', store=True, required=False, tracking=True)
    hiring_manager = fields.Char('Hiring Manager', store=True, required=False, tracking=True)
    hiring_type = fields.Char('Hiring Type', store=True, required=False)
    c_classification_level = fields.Selection([('', ''), ('director', 'Director'), ('manager', 'Manager'), ('supervisor', 'Supervisor'), ('individual_contributor', 'Individual Contributor'), ('rank_file', 'Rank and File')],'Classification/Level', store=True,readonly=False, required=False, tracking=True)
    sourcing_channel = fields.Char('Sourcing Channel', store=True, required=False)
    referrer = fields.Char('Referrer', store=True, required=False)
    c_employment_status = fields.Selection([('', ''),('probationary', 'Probationary'), ('regular', 'Regular'), ('project_based', 'Project-Based')],'Employment Status', store=True, required=False, tracking=True)
    projected_start_date = fields.Date('Projected Start Date', store=True, required=False)
    orientation_date = fields.Date('Orientation Date', store=True, required=False)
    actual_start_date = fields.Date('Actual Start Date', store=True, required=False)
    residing_within_metro_manila = fields.Selection([('yes','Yes'),('no','No')],'Residing within Metro Manila?', store=True, required=False)
    
    # Client Services Part
    training_schedule_default_shift = fields.Char('Training Schedule/Default Shift', store=True, required=False)
    system_requirement = fields.Text('System Requirement', store=True, required=False)
    instructions_for_it_team = fields.Text('Instructions for IT Team', store=True, required=False)
    training_poc = fields.Char('Training POC', store=True, required=False)
    training_poc_contact_information = fields.Char('Training POC Contact Information', store=True, required=False)
    channel_of_communication = fields.Char('Channel of Communication', store=True, required=False)
    operations_schedule = fields.Char('Operations Schedule', store=True, required=False)
    date_of_first_day_of_operations = fields.Date('Date of First Day of Operations', store=True, required=False)
    working_onsite = fields.Selection([('yes','Yes'),('no','No')],'Working Onsite?', store=True, required=False)
    
    # HR Onboarding Part 1
    verified_all_information_are_correct = fields.Char('Verified All Information Are Correct', store=True, required=False)
    medical_completed = fields.Selection([('complete','Complete'),('in_progress','In Progress'),('pending','Pending')],'Medical Completed', store=True, required=False)
    
    peme_endorsement = fields.Char('PEME Endorsement', store=True, required=False)
    peme_clinic = fields.Char('PEME Clinic?', store=True, required=False)

    peme_date_of_examination = fields.Date('Date of Examination', store=True, required=False)
    peme_validity = fields.Date('Validity', store=True, required=False)
    peme_days_left = fields.Char('Days Left', store=True, required=False)
    
    id_photo = fields.Selection([('submitted','Submitted'),('in_progress','In Progress'),('pending','Pending')],'ID Photo / 2x2', store=True, required=False)
    sss = fields.Selection([('submitted','Submitted'),('in_progress','In Progress'),('pending','Pending')],'SSS', store=True, required=False)
    sss_number = fields.Char('SSS No.', store=True, required=False, tracking=True)
    tin = fields.Selection([('submitted','Submitted'),('in_progress','In Progress'),('pending','Pending')],'TIN', store=True, required=False)
    tin_number = fields.Char('TIN No.', store=True, required=False, tracking=True)
    philhealth = fields.Selection([('submitted','Submitted'),('in_progress','In Progress'),('pending','Pending')],'PHILHEALTH', store=True, required=False)
    philhealth_number = fields.Char('PHILHEALTH No.', store=True, required=False, tracking=True)
    pag_ibig = fields.Selection([('submitted','Submitted'),('in_progress','In Progress'),('pending','Pending')],'PAG-IBIG', store=True, required=False)
    pag_ibig_number = fields.Char('HDMF No.', store=True, required=False, tracking=True)
    
    nbi_clearance = fields.Selection([('submitted','Submitted'),('in_progress','In Progress'),('pending','Pending')],'NBI Clearance', store=True, required=False)
    letter_of_undertaking = fields.Selection([('submitted','Submitted'),('in_progress','In Progress'),('pending','Pending')],'Letter of Undertaking', store=True, required=False)
    bir_2316 = fields.Selection([('submitted','Submitted'),('in_progress','In Progress'),('pending','Pending')], 'BIR 2316', store=True, required=False)
    bir_2316_endorsement_date = fields.Date('BIR 2316 Endorsement Date', store=True, required=False)
    
    okay_to_start = fields.Char('Okay to Start?', store=True, required=False)
    completed_neo = fields.Char('Completed NEO?', store=True, required=False)
    
    onboarding_forms = fields.Selection([('complete','Complete'),('in_progress','In Progress'),('pending','Pending')], 'Onboarding Forms', store=True, required=False)
    onboarding_forms_pending = fields.Text('Pending Onboarding Forms', store=True, required=False)
    
    deadline_of_primary_requirements = fields.Date('Deadline of Primary Requirements', store=True, required=False)
    deadline_of_secondary_requirements = fields.Date('Deadline of Secondary Requirements', store=True, required=False)
    
    # IT Part
    pc_ready_for_deployment = fields.Char('PC Ready for Deployment?', store=True, required=False)
    logins_created = fields.Char('NT Logins Created?', store=True, required=False)
    isw_hostgator_email_created = fields.Char('ISW Hostgator Email Created?', store=True, required=False)
    nt_logins_sent_to_employee = fields.Char('NT Logins and ISW Hotgator Email Sent to Employee?', store=True, required=False)
    signed_accountability_form_received = fields.Char('Signed Accountability Form Received?', store=True, required=False)
    
    # HR Onboarding Part 2
    email_equipment_ready_for_pickup_sent = fields.Char('Email (Equipment Ready for pickup) Sent?', store=True, required=False)
    vaccinated = fields.Char('Vaccinated?', store=True, required=False)
    projected_nh_report_sent = fields.Char('Projected NH Report Sent?', store=True, required=False)
    welcome_email_neo_invite = fields.Char('NEO Invite', store=True, required=False)
    
    # Recruitment Part
    onboarding_email = fields.Char('Onboarding Email', store=True, required=False)
    
    # Facilities Part
    prepared_gatepass_for_pick_up = fields.Char('Prepared Gatepass for Pick Up?', store=True, required=False)
    pc_released = fields.Char('PC Released?', store=True, required=False)
    work_set_up_finalized = fields.Char('Work Set Up Finalized?', store=True, required=False)
    picked_up_by = fields.Char('Picked Up By', store=True, required=False)
    new_hire_kits_released = fields.Char('New Hire Kits Released', store=True, required=False)

    # CS Part
    onboarding_report_sent_to_client = fields.Char('Onboarding Report Sent to Client?', store=True, required=False)

    # C&B Part
    mypayroll_approver = fields.Char('MyPayroll Approver', store=True, required=False, tracking=True)
    
    
    _sql_constraints = [
        ('barcode_uniq', 'unique (barcode)', "The Badge ID must be unique, this one is already assigned to another employee."),
    ]
    
    def generate_random_barcode(self):
        for employee in self:
            employee.barcode = '041'+"".join(choice(digits) for i in range(9))
    
    @api.depends('last_name', 'first_name', 'middle_name')
    def _compute_complete_name(self):
        for record in self:
            name_parts = [part for part in [record.first_name, record.middle_name, record.last_name] if part]
            record.complete_name = ' '.join(name_parts)
            
    def action_create_user(self):
        for record in self:
            existing_user = self.env['res.users'].search([('login', '=', record.employee_email_address)], limit=1)
            if existing_user:
                raise UserError(_('A user with this email already exists.'))

            # Open the confirmation wizard, passing active_id to context
            return {
                'name': _('Confirm User Creation'),
                'type': 'ir.actions.act_window',
                'res_model': 'user.confirmation.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_active_id': record.id,  # Pass the record ID to the wizard
                    'default_complete_name': record.complete_name,
                    'default_employee_id': record.employee_id,
                    'default_employee_email_address': record.employee_email_address,
                    'default_mobile_number': record.mobile_number,
                }
            }
            
    def create_user(self):
        for record in self:
            user_values = {
                'name': record.complete_name,
                'login': record.employee_email_address,
                'email': record.employee_email_address,
                'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
            }

            try:
                user = self.env['res.users'].create(user_values)
                
                # Assign the newly created user to the employee record
                record.user_id = user.id
            
                # Log message after successful creation
                self.env['mail.message'].create({
                    'body': _("User %s has been created.") % user.name,
                    'model': self._name,
                    'res_id': record.id,
                    'message_type': 'notification',
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                })
            except Exception as e:
                raise UserError(_('User creation failed: %s') % str(e))
            
            
    # @api.constrains('mobile_number')
    # def _check_phone_number_length(self):
    #     for record in self:
    #         if record.mobile_number and len(record.mobile_number) != 13:
    #             raise ValidationError("Formatted phone number must be 11 characters.")

    # @api.onchange('mobile_number')
    # def _compute_formatted_phone_number(self):
    #     for record in self:
    #         if record.mobile_number and isinstance(record.mobile_number, str) and record.mobile_number.isdigit():
    #             formatted_number = f"{record.mobile_number[:3]}-{record.mobile_number[3:6]}-{record.mobile_number[6:]}"
                
    #             # Check if the phone number starts with '0' before adding it
    #             if not formatted_number.startswith('0'):
    #                 formatted_number = '0' + formatted_number
                
    #             record.mobile_number = formatted_number
    #         else:
    #             # Handle non-numeric phone numbers or empty values
    #             record.mobile_number = record.mobile_number

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
    
    
class UserConfirmationWizard(models.TransientModel):
    _name = 'user.confirmation.wizard'
    _description = 'User Creation Confirmation Wizard'
    
    complete_name = fields.Char(string="Complete Name", required=True)
    employee_id = fields.Char('Employee ID', store=True, required=True)
    employee_email_address = fields.Char('Employee Email Address', store=True, readonly=False, required=True)
    mobile_number = fields.Char('Primary Mobile Number', store=True, readonly=False)
    
    def action_confirm(self):
        """This method is called when the user clicks Yes to confirm the action."""
        active_id = self._context.get('default_active_id')  # Get the active ID from the context
        
        if active_id:
            employee_record = self.env['hr.employee.masterlist'].browse(active_id)
            # Update the complete_name in the employee record with the new value from the wizard
            employee_record.write({
                'complete_name': self.complete_name,
                'employee_id': self.employee_id,
                'employee_email_address': self.employee_email_address,
                'mobile_number': self.mobile_number,
            })  # Call the method to create the user
            
            employee_record.create_user()
        else:
            raise UserError(_('No active employee record found.'))

    def action_cancel(self):
        """This method is called when the user clicks No to cancel the action."""
        return {'type': 'ir.actions.act_window_close'}