import datetime
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import format_date


class GeneratePayrollPeriod(models.TransientModel):
    _name = 'generate.payroll.period'
    _description = 'Generate Payroll Period'

    payment_frequency_id = fields.Many2one('hr.payment.frequency', string='Payment frequency', required=True)
    company_id = fields.Many2one("res.company", default=lambda l: l.env.company)
    year = fields.Selection([(str(year), str(year)) for year in range(datetime.datetime.now().year - 4, datetime.datetime.now().year + 6)], string='Year', required=True)
    start_period = fields.Date('Start Period', required=True)

    @api.onchange('year', 'start_period')
    def _verify_year_on_start_period(self):
        if self.year and self.start_period:
            if self.year != str(self.start_period.year):
                raise ValidationError(_('The year and the year of the beginning of the period must be the same.'))

    def compute_sheet(self):
        if not self.payment_frequency_id:
            return

        periodicities = {'MON': 30, 'BI': 15, 'WEEK': 7}
        periodicity = periodicities.get(self.payment_frequency_id.code, 0)

        if not periodicity:
            return

        hr_payroll_period_list = []
        date_from = self.start_period

        while date_from.year == int(self.year):
            date_to = date_from + relativedelta(days=periodicity - 1)
            name = {
                7: _('Weekly'),
                15: _('First Bi Weekly') if date_from.day <= 15 else _('Second Bi Weekly'),
                30: _('Monthly'),
            }[periodicity]

            vals = {
                'date_start': date_from,
                'date_end': date_to,
                'name': format_date(self.env, date_to, date_format="MMMM").capitalize() + " - " + str(self.year) + " - " + name,
                'payment_frequency_id': self.payment_frequency_id.id,
                'active': True
            }

            hr_payroll = self.env['hr.payroll.period'].create(vals)
            hr_payroll_period_list.append(hr_payroll.id)

            if periodicity == 30:
                date_from = date_from + relativedelta(months=1)
            elif periodicity == 15:
                date_from = date_from.replace(day=16) if date_from.day > 15 else date_from.replace(day=1)
            else:
                date_from = date_from + relativedelta(days=periodicity)

        return {
            'name': _('Generated Payroll Period'),
            'view_mode': 'tree,form',
            'res_model': 'hr.payroll.period',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', hr_payroll_period_list)],
        }
