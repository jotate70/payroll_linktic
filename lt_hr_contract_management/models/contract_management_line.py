from odoo import fields, models, api, _
from odoo.addons.base.models.ir_model import IrModelFields
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

from datetime import datetime, date
from typing import Tuple, Any, AnyStr
from dateutil.relativedelta import relativedelta


class ContractManagementLine(models.Model):
    _name = "contract.management.line"
    _description = "change management line for contracts"

    @api.model
    def _selection_models(self):
        model_ids = self.env['ir.model'].search([('transient', '=', False), ('state', '!=', 'manual')])
        return [(model.model, model.name) for model in model_ids if not model.model.startswith('ir.')]

    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('processed', 'Processed'),
                   ('cancelled', 'Cancelled'),
                   ('to_process', 'To Process'),
                   ('reversed', 'Reversed'),],
        required=False, default='draft', copy=False)

    class_id = fields.Many2one("contract.management.class.setting", string="Class")
    employee_id = fields.Many2one("hr.employee", copy=False)
    contract_id = fields.Many2one("hr.contract", copy=False)
    company_id = fields.Many2one("res.company", copy=False)
    management_id = fields.Many2one("contract.management", copy=False)
    field_id = fields.Many2one("ir.model.fields", string="Field", store=True)
    ttype = fields.Selection(related="field_id.ttype", string="Type", store=True)
    model_relation = fields.Char("Model Relation", default=False, copy=False)
    actual_value = fields.Char("Actual Value", compute="get_actual_value", store=True)
    actual_column_name = fields.Char("Column to fill", compute="get_actual_value", store=True)
    date_start = fields.Date(string="Start Date", copy=False, required=True)
    date_end = fields.Date(string="End Date", copy=False)
    type_relation_id = fields.Reference(selection=_selection_models, string="Relation")
    type_selection_id = fields.Many2one(
        "ir.model.fields.selection", string="Selection", domain="[('field_id', '=', field_id)]")
    type_boolean = fields.Boolean(string="Boolean", )
    type_date = fields.Date(string="Date", )
    type_datetime = fields.Datetime(string="Datetime", )
    type_monetary = fields.Monetary(string="Value", currency_field='currently_currency_id')
    type_char = fields.Char(string="Quantity")
    currently_currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    currently_company_id = fields.Many2one("res.company", compute="compute_current_company", store=True)
    company_int = fields.Integer(compute='compute_current_company', store=True, change_default=True, )
    reversed_date = fields.Datetime(string="Last Reverse date", copy=False)

    # compute methods
    @api.depends('field_id', )
    def get_actual_value(self):
        ttype_list = [key for key in sorted(fields.Field.by_type)]
        for line in self:
            value = ''
            column_name = _("Not found")
            name_field = line.field_id.name
            object_field = line.management_id.contract_id
            _type = line.ttype

            if not _type or _type not in ttype_list:
                raise ValidationError(_("The field type %s does not exist in Odoo") % line.ttype)

            if line.management_id.state == 'processed':
                line.actual_value = line._origin.actual_value
                line.actual_column_name = line._origin.actual_column_name
                continue
            if not object_field:
                line.actual_value = _("No contract defined")

            field_value = getattr(object_field, name_field)

            if _type in ('char', 'date', 'boolean', 'datetime', 'float', 'integer', 'monetary', 'text'):

                if isinstance(field_value, str):
                    value = field_value
                    column_name = _("Quantity")
                elif isinstance(field_value, fields.date):
                    value = str(field_value)
                    column_name = _("Date")
                elif isinstance(field_value, fields.datetime):
                    column_name = _("Datetime")
                    value = str(field_value)
                elif isinstance(field_value, bool):
                    column_name = _("Boolean")
                    value = _("True") if field_value else _("False")
                elif isinstance(field_value, int) or isinstance(field_value, float):
                    column_name = _("Quantity")
                    value = str(field_value)

            elif _type == 'selection':
                # return the selection list (pairs (value, label)); labels are
                # translated according to context language ---> line.env : env.lang
                values_translated = dict(object_field._fields[name_field]._description_selection(line.env))
                value = values_translated.get(field_value, None) or _("Selection value not found")
                column_name = _("Selection")

            elif _type in ('many2one',):
                name = field_value._rec_name
                if name:
                    value = getattr(field_value, name)
                else:
                    value = getattr(field_value, 'display_name') or _('Name not found')
                column_name = _("Relation")

            line.actual_value = value
            line.actual_column_name = column_name

    @api.depends('management_id',
                 'management_id.company_id',)
    def compute_current_company(self):
        for line in self:
            company = line.management_id.company_id or self.env.company

            line.currently_company_id = company
            line.company_int = company and company.id or 0

    # onchange methods
    @api.onchange('type_relation_id')
    def onchange_relation_type(self):
        self.validate_allowed_company()

    # custom methods
    def get_field_value(self) -> Tuple[AnyStr, Any, IrModelFields]:
        try:
            self.ensure_one()
        except ValueError as e:
            raise ValidationError(_("Please, contact to administrator\n\n.Expected singleton: %s" % self))

        field_name = self.field_id.name
        field_value = None

        if self.ttype in ('char', 'text', 'float', 'integer'):
            value = self.type_char
            if self.ttype == 'float':
                float(value)
            elif self.ttype == 'integer':
                int(value)
            field_value = value

        elif self.ttype in ('boolean',):
            field_value = self.type_boolean
        elif self.ttype in ('date',):
            field_value = self.type_date
        elif self.ttype in ('datetime',):
            field_value = self.type_datetime
        elif self.ttype in ('monetary',):
            field_value = self.type_monetary
        elif self.ttype in ('selection',):
            value = self.type_selection_id  # ir.model.fields.selection
            field_value = value.value  # [(value, name), (value, name)]
        elif self.ttype == 'many2one':
            field_value = self.type_relation_id.id
        return field_name, field_value, self.field_id

    def get_company_domain(self, model_relation: str, company_int: int) -> [(str, str, str), ]:
        domain = []
        company_id = self.env['res.company'].browse(company_int)

        if not model_relation or not company_id:
            return domain

        model_id = self.env['ir.model'].search([('model', '=', model_relation)])
        _domain = []
        _search = [('model_id', '=', model_id.id), ('store', '=', True), ('relation', '=', 'res.company')]

        if model_id:
            m2o_search = list(_search) + [('ttype', '=', 'many2one')]
            _domain += self._get_domain(m2o_search, '=', company_id.id)

            m2m_search = list(_search) + [('ttype', '=', 'many2many')]
            _domain += self._get_domain(m2m_search, 'in', company_id.id)

            domain += self.format_domain(_domain)
        return domain

    def _get_domain(self, search_criteria: list, operator: str, value: int) -> list:
        domain = []
        search_method = self.env['ir.model.fields'].search
        field_ids = search_method(search_criteria)

        if not field_ids:
            return []

        for field in field_ids:
            domain.append((field.name, '=', False))
            domain.append((field.name, operator, value))

        return domain

    def set_date(self, log_id):
        try:
            self.ensure_one()
        except ValueError as e:
            raise ValidationError(_("Please, contact to administrator\n\n.Expected singleton: %s" % self))

        domain = [('contract_id', '=', self.contract_id.id),
                  ('management_id.state', '=', 'processed'),
                  ('class_id', '=', self.class_id.id),
                  ('date_start', '<=', self.date_start)]
        history_management = self.search(domain, order='date_start ASC')

        # Get log line for reverse purposes

        contract_log_line = self.env['contract.management.log.line']

        if history_management:

            line_id = history_management[-1]
            line = contract_log_line.prepare_log_line(
                'date_end', line_id, line_id.management_id, 'write_line_dates', log_id=log_id)

            line_id.write({'date_end': self.date_start - relativedelta(days=1)})

            contract_log_line += self.env['contract.management.log.line'].create([line])

        return contract_log_line

    def get_reference_name(self, company_int: int, model_relation: str = '', name: str = '', operator: str = 'ilike', limit: int = 100,
                           args=None) -> [(int, str), ]:

        """
        Dynamic domain given domain_relation.
        Args:
            :param str company_int: Given company id
            :param str model_relation: Given model name
            :param str name: the name pattern to match
            :param list args: optional search domain
            :param str operator: domain operator for matching ``name``, such as 'like'`` or ``'='``.
            :param int limit: optional max number of records to return
        Returns:
            return: list of pairs ``(id, text_repr)`` for all matching records.
        """
        # hook to get domain
        args += self.get_company_domain(model_relation, company_int)
        names = self.env[model_relation].name_search(name, args, operator, limit)
        return {'names': names, 'domain': args}

    def set_reverse_state(self, reversed_date):
        for line in self:
            line.write({'state': 'reversed', 'date_end': False, 'reversed_date': reversed_date})

    # Validation methods

    def validate_lines(self):
        for line in self:
            if not line.date_start:
                raise UserError(_("The start date of class %s cannot be empty") % line.class_id.name)

            if not line.field_id:
                raise ValidationError(_("The field on the class %s cannot be empty") % line.class_id.name)

            if line.ttype in ('char', 'text', 'float', 'integer'):
                if not line.type_char:
                    raise UserError("The column Value cannot be empty for this class %s" % line.class_id.name)
                try:
                    if line.ttype == 'float':
                        float(line.type_char)
                    elif line.ttype == 'integer':
                        int(line.type_char)
                except ValueError:
                    raise UserError(_("In the column Value %s must be a number") % line.type_char)

            elif line.ttype in ('boolean',) and not line.type_boolean:
                raise UserError(_("The column Boolean cannot be empty for this class %s" % line.class_id.name))
            elif line.ttype in ('date',) and not line.type_date:
                raise UserError(_("The column Date cannot be empty for this class %s" % line.class_id.name))
            elif line.ttype in ('datetime',) and not line.type_datetime:
                raise UserError(_("The column Datetime cannot be empty for this class %s" % line.class_id.name))
            elif line.ttype in ('monetary',) and line.type_monetary <= 0:
                raise UserError(_("The column Monetary cannot be empty for this class %s" % line.class_id.name))
            elif line.ttype in ('selection',) and not line.type_selection_id:
                raise UserError(_("The column Selection cannot be empty for this class %s" % line.class_id.name))
            elif line.ttype == 'many2one':
                if not line.type_relation_id:
                    raise UserError(_("The column relation cannot be empty for this class %s" % line.class_id.name))
                line.validate_allowed_company()

    # model methods
    @api.constrains('type_relation_id')
    def validate_allowed_company(self):
        for line in self:
            if line.type_relation_id and line.ttype == 'many2one':
                company_domain = self.get_company_domain(line.model_relation, line.company_int)
                fields_set_m2o = set()
                fields_set_m2m = set()
                for _tuple in company_domain:
                    if not _tuple or not isinstance(_tuple, tuple) or not _tuple[-1]:
                        continue
                    if _tuple[0] and _tuple[1] and isinstance(_tuple[0], str) and isinstance(_tuple[1], str):
                        if _tuple[1] == '=':
                            fields_set_m2o.add(_tuple[0])
                        elif _tuple[1] == 'in':
                            fields_set_m2m.add(_tuple[0])

                if fields_set_m2o or fields_set_m2m:
                    for m2o_field in fields_set_m2o:
                        company = getattr(line.type_relation_id, m2o_field)
                        if company:
                            if not line.currently_company_id == company:
                                msg_line = _(
                                    "The relation of field %s not belong to %s.The company relation cannot be different.")
                                raise UserError(msg_line % (line.field_id.complete_name, company.name))

                    for m2m_field in fields_set_m2o:
                        company = getattr(line.type_relation_id, m2m_field)
                        if company:
                            if line.currently_company_id not in company:
                                msg_line = _("The relation chosen has multiple companies. The company on contract "
                                             "management must be within the group of companies in the relation")
                                raise UserError(msg_line % company)

    @api.model
    def format_domain(self, domain) -> list:
        length = len(domain)
        if not domain or len(domain) <= 1:
            return domain
        return ['|'] * (length-1) + domain

    def unlink(self):
        for line in self:
            if line.state not in ('draft',):
                raise UserError(
                    _("Delete operation not allowed. Only in draft state is allowed this operation"))
        return super(ContractManagementLine, self).unlink()
