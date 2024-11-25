import pytz

from collections import defaultdict
from datetime import datetime, timedelta
from operator import itemgetter
from pytz import timezone

from odoo import models, fields, api, exceptions, _
from odoo.addons.resource.models.utils import Intervals
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.exceptions import AccessError
from odoo.tools import format_duration

class Attendance(models.Model):
    _name = "hrms.attendance"
    _description = "Attendance"
    _order = "check_in desc"
    _inherit = [ 'mail.thread', 'mail.activity.mixin']

    def _default_employee(self):
        return self.env.user.employee_id
    
    employee_name_id = fields.Many2one("res.users", string="Employee", default=lambda self: self.env.user.id , required=True, ondelete='cascade', index=True)
    # employee_id = fields.Char('Employee ID', store=True, tracking=True)
    user_id = fields.Char('User ID Reference', store=True)
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=True)
    check_out = fields.Datetime(string="Check Out")
    old_check_in = fields.Datetime("Old Check In", readonly=True, tracking=True, store=True)
    reason_check_in = fields.Char("Updated Check In Remarks")
    old_check_out = fields.Datetime("Old Check Out", readonly=True, tracking=True, store=True)
    reason_check_out = fields.Char("Updated Check Out Remarks")
    updated_by_check_in_id = fields.Many2one('res.users', string='Updated By', store=True)
    updated_by_check_out_id = fields.Many2one('res.users', string='Updated By', store=True)
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)
    # worked_hours = fields.Float(string='Worked Hours', store=True, readonly=True)
    # overtime_hours = fields.Float(string="Over Time", compute='_compute_overtime_hours', store=True)
    overtime_hours = fields.Float(string="Over Time", store=True)
    in_country_name = fields.Char(string="Country", help="Based on IP Address", readonly=True)
    in_city = fields.Char(string="City", readonly=True)
    in_ip_address = fields.Char(string="IP Address", readonly=True)
    in_browser = fields.Char(string="Browser", readonly=True)
    in_mode = fields.Selection(string="Mode",
                               selection=[('kiosk', "Kiosk"),
                                          ('systray', "Systray"),
                                          ('manual', "Manual")],
                               readonly=True,
                               default='manual')
    out_country_name = fields.Char(help="Based on IP Address", readonly=True)
    out_city = fields.Char(readonly=True)
    out_ip_address = fields.Char(readonly=True)
    out_browser = fields.Char(readonly=True)
    out_mode = fields.Selection(selection=[('kiosk', "Kiosk"),
                                           ('systray', "Systray"),
                                           ('manual', "Manual")],
                                readonly=True,
                                default='manual')

    break_time_start = fields.Datetime("Break Time Start")
    break_time_end = fields.Datetime("Break Time End")
    break_time_total = fields.Float("Total Break Time", compute='_compute_time_difference', store=True)

    is_flexible = fields.Boolean(string="Flexible Schedule", default=False)

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        """ Computes the worked hours of the attendance record.
            Worked hours are calculated as the difference between check-in and check-out times,
            with optional lunch break intervals subtracted."""
        for attendance in self:
            if attendance.check_out and attendance.check_in:
                default_tz = timezone('UTC')
                check_in_tz = attendance.check_in.astimezone(default_tz)
                check_out_tz = attendance.check_out.astimezone(default_tz)

                total_interval = check_out_tz - check_in_tz

                lunch_break = timedelta(hours=1) if not attendance.is_flexible else timedelta(0)

                worked_duration = total_interval - lunch_break
                attendance.worked_hours = worked_duration.total_seconds() / 3600.0
            else:
                attendance.worked_hours = 0.0

    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ verifies if check_in is earlier than check_out. """
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                if attendance.check_out < attendance.check_in:
                    raise exceptions.ValidationError(_('"Check Out" time cannot be earlier than "Check In" time.'))
                
    @api.constrains('check_in', 'check_out', 'employee_name_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        for attendance in self:
            # we take the latest attendance before our check_in time and check it doesn't overlap with ours
            last_attendance_before_check_in = self.env['hrms.attendance'].search([
                ('employee_name_id', '=', attendance.employee_name_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out > attendance.check_in:
                raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s",
                                                   empl_name=attendance.employee_name_id.name,
                                                   datetime=format_datetime(self.env, attendance.check_in, dt_format=False)))

            if not attendance.check_out:
                # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                no_check_out_attendances = self.env['hrms.attendance'].search([
                    ('employee_name_id', '=', attendance.employee_name_id.id),
                    ('check_out', '=', False),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if no_check_out_attendances:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee hasn't checked out since %(datetime)s",
                                                       empl_name=attendance.employee_name_id.name,
                                                       datetime=format_datetime(self.env, no_check_out_attendances.check_in, dt_format=False)))
            else:
                # we verify that the latest attendance with check_in time before our check_out time
                # is the same as the one before our check_in time computed before, otherwise it overlaps
                last_attendance_before_check_out = self.env['hrms.attendance'].search([
                    ('employee_name_id', '=', attendance.employee_name_id.id),
                    ('check_in', '<', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s",
                                                       empl_name=attendance.employee_name_id.name,
                                                       datetime=format_datetime(self.env, last_attendance_before_check_out.check_in, dt_format=False)))
                
    def get_kiosk_url(self):
        return self.get_base_url() + "/hrms_attendance/" + self.env.company.attendance_kiosk_key
    
    def action_try_kiosk(self):
        if not self.env.user.has_group("hrms_attendance.group_hrms_attendance_admin"):
            return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("You don't have the rights to execute that action."),
                        'type': 'info',
                    }
            }
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.env.company.attendance_kiosk_url + '?from_trial_mode=True'
        }