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


class HR_Dependency(models.Model):
    _name = 'hr.dependency'
    _description = 'Dependency'
    _rec_name = 'principal_name_id'

    active = fields.Boolean('Active', store=True, default=True)
    principal_name_id = fields.Many2one('hr.employee.masterlist','Principal Name', store=True, readonly=False)
    dependent_name = fields.Char('Dependent Name', store=True, readonly=False)
    relation = fields.Char('Relation', store=True, readonly=False)
    dob = fields.Date('Date of Birth', store=True, readonly=False)
    contact_number = fields.Char('Contact No.', store=True, readonly=False)