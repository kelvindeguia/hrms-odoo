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


class HR_Job_Position(models.Model):
    _name = 'hr.job.positions'
    _description = 'Job Position'
    _rec_name = 'job_position'

    active = fields.Boolean('Active', store=True, default=True)
    job_position = fields.Char('Job Position', store=True, readonly=False)