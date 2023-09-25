from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    novelty_ids = fields.One2many('hr.novelty', 'payslip_id', string="Novelty's")

    def compute_sheet(self):
        res = super(HrPayslip, self).compute_sheet()
        for rec in self:

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

            # Delete all objects
            for line in rec.earn_ids:
                rec.earn_ids = [(2, line.id)]
            for line in rec.deduction_ids:
                rec.deduction_ids = [(2, line.id)]

            for novelty in novelties:
                if novelty.type == 'income':
                    rec.earn_ids = [(0, 0, {
                        'name': novelty.novelty_type_id.name,
                        'amount': novelty.value,
                        'quantity': novelty.quantity,
                        'total': novelty.value,
                        'date_start': novelty.date_start,
                        'date_end': novelty.date_end,
                    })]

                elif novelty.type == 'deduction':
                    rec.deduction_ids = [(0, 0, {
                        'name': novelty.novelty_type_id.name,
                        'amount': novelty.value,
                        'quantity': novelty.quantity,
                        'total': novelty.value,
                        'date_start': novelty.date_start,
                        'date_end': novelty.date_end,
                    })]
        return res
