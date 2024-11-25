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


class HR_Department(models.Model):
    _name = 'hr.departments'
    _description = 'Departments'
    _rec_name = 'department_name'

    active = fields.Boolean('Active', store=True, default=True)
    department_name = fields.Char('Department Name', store=True, readonly=False)
    manager_id = fields.Many2one('hr.employee.masterlist', 'Manager', store=True, readonly=False)
    parent_id = fields.Many2one('hr.departments', 'Parent Department', store=True, readonly=False)
    child_ids = fields.One2many('hr.departments', 'parent_id')
    company = fields.Selection([('isupport_worldwide','iSupport Worldwide'),('iswerk','ISWerk' )],string='Company', store=True, readonly=False)