from odoo import models, fields


class HrNoveltyType(models.Model):
    _name = 'hr.novelty.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Payroll Novelty Type'

    name = fields.Char(string='Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, tracking=True)
    category_id = fields.Many2one('hr.novelty.category', string='Category', required=True, tracking=True)
    type = fields.Selection([('income', 'Income'), ('deduction', 'Deduction')], string='Type', required=True,
                            tracking=True)
    apply_factor = fields.Boolean(related='category_id.apply_factor', string='Apply Factor', store=True, tracking=True)
    factor = fields.Float(string='Factor', tracking=True)
    apply_date_end = fields.Boolean(string='Apply Date End', default=False, required=True, tracking=True)
    formula = fields.Html(string='Formula')
