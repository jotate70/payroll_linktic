from odoo import fields, models, api, _
from odoo.addons.base.models.ir_model import IrModelFields
from odoo.tools.safe_eval import safe_eval

from typing import Any, AnyStr, Dict
from dateutil.parser import parse


class ContractManagementLog(models.Model):
    _name = 'contract.management.log'
    _description = 'Contract Management Reversed'
    _rec_name = 'display_name'

    name = fields.Char(string="name")
    reversed_date = fields.Datetime(string="Reversed Management ")
    date = fields.Datetime(string="Measure applied")
    state = fields.Selection(
        string='state',
        selection=[('actual', 'Actual'),
                   ('reversed', 'Reversed'), ], )
    management_id = fields.Many2one("contract.management", string="Contract Management")
    contract_id = fields.Many2one("hr.contract", "Contract")
    line_ids = fields.One2many("contract.management.log.line", "log_id", "Changes Applied")

    def _compute_display_name(self):
        for record in self:
            record.display_name = _('Log: %s - %s') % (record.name or '/', record.contract_id.name or _("No Contract"))

    def set_reverse(self, reverse_date: fields.Date):
        for log in self:
            log.write({'state': 'reversed', 'reversed_date': reverse_date})
            if log.line_ids:
                log.line_ids.write({'state': 'reversed', 'reverse_date': reverse_date})


class ContractManagementLogLine(models.Model):
    _name = 'contract.management.log.line'
    _description = 'Contract management Log'

    field_id = fields.Many2one("ir.model.fields", "Field")
    management_id = fields.Many2one("contract.management", string="Contract Management")
    log_id = fields.Many2one("contract.management.log", string="Log")

    state = fields.Selection(
        string='state',
        selection=[('actual', 'Actual'),
                   ('reversed', 'Reversed'), ], )

    model_to_affect = fields.Char("Model to affect")
    id_to_affect = fields.Integer()
    method = fields.Char(string="method")

    value = fields.Char(string="Value applied", )
    value_to_show = fields.Char(string="Value applied", compute="_compute_values_to_show",
                                help="Value before to process measure. Value to change in case of reversion")

    old_value = fields.Char(string="Value before reversion", )
    old_value_to_show = fields.Char(string="Value before reversion", compute="_compute_values_to_show",
                                    help="Value after to process measure. Value before to reversion process")

    reverse_date = fields.Datetime(string="Reversed Date")
    date = fields.Datetime(string="Change applied")

    args = fields.Char()  # must be a list []
    kwargs = fields.Char()  # must be a list dict

    # depends methods

    def _compute_values_to_show(self):
        for log_line in self:
            n1 = log_line.value or ''  # Value applied
            n2 = log_line.old_value or ''  # Value before reversion
            if n1:
                n1 = log_line.get_name_value(log_line.model_to_affect, n1, log_line.field_id)
            if n2:
                n2 = log_line.get_name_value(log_line.model_to_affect, n2, log_line.field_id)

            log_line.value_to_show = n1 or _('No value yet')
            log_line.old_value_to_show = n2 or _('No value yet')

    # custom methods

    def make_reverse(self, date_reversed: fields.Date):
        for line in self:
            if line.state not in ('actual',) or not line.method:
                continue

            args = []
            kwargs = {}

            if line.args:
                _eval = safe_eval(line.args)
                if isinstance(_eval, list):
                    args = _eval
            if line.kwargs:
                _eval = safe_eval(line.kwargs)
                if isinstance(_eval, dict):
                    kwargs = _eval

            method = getattr(self, line.method)
            old_value = method(*args, **kwargs)
            line.write({'old_value': old_value})

    def write_line_char(self, *args, **kwargs) -> Any:
        """
        Args:
            *args :: List: args from log line
            **kwargs :: Dict: kwargs from log line

        Returns: Any
        """
        self.ensure_one()

        if not args:
            args = []
        if not kwargs:
            kwargs = {}

        if self.value in ('False', 'None'):
            value = False
        else:
            value = str(self.value)

        record = self.get_record(is_sudo=kwargs.get('with_sudo', False))
        old_value = getattr(record, self.field_id.name)
        record.write({self.field_id.name: value})

        return str(old_value)

    def write_line_many2one(self, *args, **kwargs) -> Any:
        """
        rgs:
            *args :: List: args from log line
            **kwargs :: Dict: kwargs from log line

        Returns: Any
        """
        self.ensure_one()

        if not args:
            args = []
        if not kwargs:
            kwargs = {}

        if self.value in ('False', 'None'):
            value = False
        else:
            value = int(self.value)

        record = self.get_record(is_sudo=kwargs.get('with_sudo', False))
        old_value = getattr(record, self.field_id.name)
        record.write({self.field_id.name: value})

        return str(old_value.id)

    def write_line_many2many(self, *args, **kwargs) -> Any:
        """
        rgs:
            *args :: List: args from log line
            **kwargs :: Dict: kwargs from log line

        Returns: Any
        """
        self.ensure_one()

        if not args:
            args = []
        if not kwargs:
            kwargs = {}

        ids = safe_eval(self.value)
        value = [(6, 0, ids)]
        if not ids:
            value = False

        record = self.get_record(is_sudo=kwargs.get('with_sudo', False))
        old_value = str(args)
        record.write({self.field_id.name: value})

        return old_value

    def delete_many2one(self, *args, **kwargs) -> Any:
        """
        rgs:
            *args :: List: args from log line
            **kwargs :: Dict: kwargs from log line

        Returns: Any
        """
        self.ensure_one()

        if not args:
            args = []
        if not kwargs:
            kwargs = {}

        record = self.get_record(is_sudo=kwargs.get('with_sudo', False))
        record.unlink()

        return ''

    def write_line_dates(self, *args, **kwargs) -> Any:
        """
        rgs:
            *args :: List: args from log line
            **kwargs :: Dict: kwargs from log line

        Returns: Any
        """
        self.ensure_one()

        if not args:
            args = []
        if not kwargs:
            kwargs = {}

        if self.value in ('False', 'None'):
            time_obj = False
        else:
            time_obj = parse(self.value)

            if self.field_id.ttype == 'date':
                time_obj = time_obj.date()

        record = self.get_record(is_sudo=kwargs.get('with_sudo', False))
        old_value = getattr(record, self.field_id.name)
        record.write({self.field_id.name: time_obj})

        return str(old_value)

    def write_line_boolean(self, *args, **kwargs) -> Any:
        """
        rgs:
            *args :: List: args from log line
            **kwargs :: Dict: kwargs from log line

        Returns: Any
        """
        self.ensure_one()

        if not args:
            args = []
        if not kwargs:
            kwargs = {}

        boolean = True if self.value == 'True' else False

        record = self.get_record(is_sudo=kwargs.get('with_sudo', False))
        old_value = getattr(record, self.field_id.name)
        record.write({self.field_id.name: boolean})

        return str(old_value)

    def write_line_number(self, *args, **kwargs) -> Any:
        """
        rgs:
            *args :: List: args from log line
            **kwargs :: Dict: kwargs from log line

        Returns: Any
        """
        self.ensure_one()

        if not args:
            args = []
        if not kwargs:
            kwargs = {}

        if self.value in ('False', 'None'):
            value = False
        else:
            if self.field_id.ttype == 'integer':
                value = int(self.value)
            else:
                value = float(self.value)

        record = self.get_record(is_sudo=kwargs.get('with_sudo', False))
        old_value = getattr(record, self.field_id.name)
        record.write({self.field_id.name: value})

        return str(old_value)

    def get_name_value(self, model_to_affect, value, _field) -> Any:
        self.ensure_one()
        _type = _field.ttype
        this = _('Name not found')

        if _type in ('char', 'date', 'selection', 'datetime', 'float', 'integer', 'monetary', 'text'):
            this = value

        elif _type == 'boolean':
            this = _("True") if value == 'True' else _("False")

        elif _type in ('many2one',):
            try:
                this_id = int(value)
            except ValueError:
                this_id = False
                this = _("Empty")
            if isinstance(this_id, int):
                odoo_object_id = self.env[_field.relation].browse(this_id)
                if odoo_object_id:
                    this = odoo_object_id.display_name or odoo_object_id._rec_name

        elif _type in ('many2many',):
            values_name = []
            this_ids = safe_eval(self.value)
            odoo_object_ids = self.env[_field.relation].browse(this_ids)
            for odoo_object_id in odoo_object_ids:
                _this = odoo_object_id.display_name or odoo_object_id._rec_name
                values_name.append(str(this))
            if values_name:
                this = '--'.join(values_name)
        return this

    def prepare_log_line(self, field_name, odoo_object, management, method, log_id=None, args=None, kwargs=None) -> Dict:
        field_id = self.get_field_id(field_name, odoo_object)
        value = getattr(odoo_object, field_name)

        if field_id.ttype in ('many2one', 'many2many') and not value:
            value = False
        elif field_id.ttype == 'many2one' and value:
            value = value.id
        elif field_id.ttype == 'many2many' and value:
            value = value.ids

        line = {
            'field_id': field_id.id,
            'management_id': management.id,
            'state': 'actual',
            'model_to_affect': odoo_object._name,
            'id_to_affect': odoo_object.id,
            'value': str(value),
            'method': method,
            'date': fields.datetime.now(),
        }

        if log_id:
            line.update({
                'log_id': log_id.id
            })

        if args:
            line.update({
                'args': str(args)
            })
        if kwargs:
            line.update({
                'kwargs': str(kwargs)
            })
        return line

    def create_log_line(self, field_name, odoo_object, management, method, log_id=None, args=None, kwargs=None) -> Any:
        line = self.prepare_log_line(field_name, odoo_object, management, method, log_id=log_id, args=args, kwargs=kwargs)
        line_id = self.create([line])
        return line_id

    def get_field_id(self, field_name, odoo_object) -> IrModelFields:
        model_id = self.env['ir.model'].search([('model', '=', odoo_object._name)])
        field_id = self.env['ir.model.fields'].search([('model_id', '=', model_id.id), ('name', '=', field_name)])
        return field_id

    def get_model(self, is_sudo=False) -> Any:
        model_env = self.env[self.model_to_affect]
        if is_sudo:
            model_env = self.env[self.model_to_affect].sudo()
        return model_env

    def get_record(self, is_sudo=False) -> Any:
        model_env = self.get_model(is_sudo)
        return model_env.browse(self.id_to_affect)

