from odoo import models, fields, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    novelty_ids = fields.One2many('hr.novelty', 'payslip_id', string="Novelty's")

    # Method of adding novelty income and deductions
    def compute_sheet(self):
        res = super(HrPayslip, self).compute_sheet()
        for rec in self:

            # Delete all objects
            for line in rec.earn_ids:
                rec.earn_ids = [(2, line.id)]
            for line in rec.deduction_ids:
                rec.deduction_ids = [(2, line.id)]

            # Earn for worked days
            worked_line = rec.worked_days_line_ids.filtered(lambda l: l.code == 'WORK100')
            if worked_line:
                amount = rec.contract_id.wage / 30
                total = worked_line.number_of_days * (rec.contract_id.wage / 30)
                rec.earn_ids = [(0, 0, {
                    'name': _("Basic Wage"),
                    'amount': amount,
                    'quantity': worked_line.number_of_days,
                    'total': total,
                    'date_start': rec.date_from,
                    'date_end': rec.date_to,
                    'computed': False,
                })]

            noveltys_not_date_end = rec.env['hr.novelty'].search([
                ('contract_id', '=', rec.contract_id.id), ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approval'), ('date_start', '<=', rec.date_to), ('date_end', '=', False)
            ])

            noveltys_date_end = rec.env['hr.novelty'].search([
                ('contract_id', '=', rec.contract_id.id), ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approval'),
                ('date_start', '<=', rec.date_to), ('date_end', '!=', False),
                ('date_end', '>=', rec.date_from)
            ])

            novelties = noveltys_not_date_end + noveltys_date_end
            rec.novelty_ids = [(6, 0, novelties.ids)]

            for novelty in novelties:
                date_end = novelty.date_end if novelty.date_end else novelty.date_start
                if novelty.type == 'income':
                    rec.earn_ids = [(0, 0, {
                        'name': novelty.novelty_type_id.name,
                        'amount': novelty.value,
                        'quantity': novelty.quantity,
                        'total': novelty.value,
                        'date_start': novelty.date_start,
                        'date_end': date_end,
                        'computed': False,
                    })]

                elif novelty.type == 'deduction':
                    rec.deduction_ids = [(0, 0, {
                        'name': novelty.novelty_type_id.name,
                        'amount': novelty.value,
                        'quantity': novelty.quantity,
                        'total': novelty.value,
                        'date_start': novelty.date_start,
                        'date_end': date_end,
                        'computed': False,
                    })]

        return res
