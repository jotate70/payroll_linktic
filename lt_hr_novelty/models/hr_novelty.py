from odoo import models, fields, api


class HrNovelty(models.Model):
    _name = 'hr.novelty'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Novelty of Payroll'

    name = fields.Char(string='Name', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    wage = fields.Monetary('Wage', help="Wage", related='contract_id.wage')
    date_start = fields.Date(string='Date Start', required=True, default=fields.Date.today(), tracking=True)
    date_end = fields.Date(string='Date End', tracking=True)
    novelty_type_id = fields.Many2one('hr.novelty.type', string='Novelty Type', required=True, tracking=True)
    code = fields.Char(string='Code', related='novelty_type_id.code', tracking=True)
    type = fields.Selection([('income', 'Income'), ('deduction', 'Deduction')], string='Type',
                            related='novelty_type_id.type', store=True)
    quantity = fields.Integer(string='Quantity', required=True, tracking=True)
    value = fields.Float(string='Value', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approval', 'Approved'),
        ('rejected', 'Refused'),
    ], string='State', default='draft', required=True, tracking=True)
    factor = fields.Float(related='novelty_type_id.factor', string='Factor', tracking=True)
    apply_date_end = fields.Boolean(related='novelty_type_id.apply_date_end', string='Apply Date End', store=True,
                                    tracking=True)
    formula = fields.Html(related='novelty_type_id.formula', string='Formula')
    payslip_id = fields.Many2one('hr.payslip', string="Payslip")

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_pending_approval(self):
        self.write({'state': 'pending_approval'})

    def action_approval(self):
        self.write({'state': 'approval'})

    def action_rejected(self):
        self.write({'state': 'rejected'})
