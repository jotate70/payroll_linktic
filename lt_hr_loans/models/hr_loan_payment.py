from odoo import fields, models, api, _


class HrLoanPayment(models.Model):
    _name = 'hr.loan.payment'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Loan Payment for Loan'

    loan_id = fields.Many2one('hr.loan', string="Loan ID", required=True)
    novelty_id = fields.Many2one('hr.novelty', string="Novelty ID")
    date = fields.Date(string="Date", required=True)
    value = fields.Float(string="Value", required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('generated', 'Generated'),
        ('paid', 'Paid'),
    ], string="State", readonly=True,
        default="pending")

    def generate_novelty(self):
        for record in self:
            record.write({
                'state': 'generated'
            })
            loan_id = record.loan_id
            novelty_id = record.env['hr.novelty'].create({
                'employee_id': loan_id.employee_id.id,
                'contract_id': loan_id.contract_id.id,
                'date_start': record.date,
                'date_end': record.date,
                'novelty_type_id': loan_id.type_loan_id.novelty_type_id.id,
                'quantity': 1,
                'value': record.value,
            })
            record.novelty_id = novelty_id.id
            record.loan_id.novelty_ids = [(4, novelty_id.id)]

    def action_view_novelty(self):
        return {
            'name': _('Novelty From Loan'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'res_model': 'hr.novelty',
            'target': 'new',
            'res_id': self.novelty_id.id,
        }

    def paid_novelty(self):
        for record in self:
            record.write({
                'state': 'paid'
            })
            record.novelty_id.action_pending_approval()
            record.novelty_id.action_approval()
            record.loan_id.recalculated_paid_value()
