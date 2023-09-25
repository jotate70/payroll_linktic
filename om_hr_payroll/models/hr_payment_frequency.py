from odoo import fields, models, api, _


class HrPaymentFrequency(models.Model):
    _name = 'hr.payment.frequency'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Frequencies of payroll periods'

    name = fields.Selection([('monthly', 'Monthly'), ('bi_weekly', 'Bi-Weekly'), ('week', 'Week')], string='Name',
                            required=True)
    code = fields.Char(string='Code', readonly=True)
    company_id = fields.Many2many('res.company', relation="hr_payment_company_rel", column1="hr_payment_id",
                                  column2="company_id", string='Company', default=lambda self: self.env.company)
    company_ids = fields.Many2many('res.company', compute="compute_current_companies")

    @api.depends('company_id')
    def compute_current_companies(self):
        for payment in self:
            payment.company_ids = payment.env.companies

    @api.onchange('name')
    def _default_value_code(self):
        for record in self:
            if record.name:
                if record.name == 'monthly':
                    record.code = 'MON'
                if record.name == 'bi_weekly':
                    record.code = 'BI'
                if record.name == 'week':
                    record.code = 'WEEK'

    def name_get(self):
        return [(record.id, _(dict(self._fields['name'].selection).get(record.name))) for record in self]
