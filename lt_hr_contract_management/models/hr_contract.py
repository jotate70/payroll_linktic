from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    salary_type = fields.Selection(
        [('basic', 'Basic'), ('integral', 'Integral'),
         ('support_sustainability', 'Support Sustainability')], required=True, tracking=True)
