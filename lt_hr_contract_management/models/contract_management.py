from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
from odoo.addons.base.models.ir_model import IrModelFields
from odoo import fields, models, api, _, SUPERUSER_ID
from typing import Tuple, Dict, List, AnyStr
from pytz import timezone
import logging
from .contract_management_log import ContractManagementLog
_logger = logging.getLogger(__name__)


def today_timezone(this: AnyStr = 'America/Bogota') -> Tuple[fields.datetime, fields.date]:
    user_timezone = timezone(this)
    datetime_now = user_timezone.localize(fields.Datetime.now())

    offset = datetime_now.utcoffset()

    real_time = datetime_now + offset

    real_today = real_time.date()

    return real_time, real_today


class ContractManagement(models.Model):
    _name = 'contract.management'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Change management for contracts'

    READONLY_STATES = {
        "draft": [("readonly", False)],
        "processed": [("readonly", True)],
        "reversed": [("readonly", True)],
        "cancelled": [("readonly", True)],
        "to_process": [("readonly", True)]
    }

    name = fields.Char("Name", index=True, states=READONLY_STATES, copy=False)
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('processed', 'Processed'),
                   ('reversed', 'Reversed'),
                   ('to_process', 'To Process'),
                   ('cancelled', 'Cancelled'), ],
        required=False, default='draft', copy=False)

    type_id = fields.Many2one("contract.management.reason.setting", "Reason", states=READONLY_STATES)
    ttype_id = fields.Many2one("contract.management.type.setting", "Type", related="type_id.type_id", )
    employee_id = fields.Many2one("hr.employee", string="Employee", states=READONLY_STATES,
                                  domain="[('company_id', '=', actual_company_id)]")
    identification = fields.Char("Identification Number", related="employee_id.identification_id")
    contract_id = fields.Many2one("hr.contract", string='Contract', required=True, tracking=True)
    company_id = fields.Many2one("res.company", string='Company', required=True, readonly=True, traking=True)

    actual_company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    ui_company_id = fields.Many2one("res.company", compute="_compute_current_company")
    line_ids = fields.One2many("contract.management.line", "management_id", states=READONLY_STATES,
                               string="Line Change")
    date_init = fields.Date("Start Date", copy=False, states=READONLY_STATES, )

    reversed_date = fields.Datetime(string="Last Reverse date", copy=False)
    log_ids = fields.One2many("contract.management.log", 'management_id', string="Logs")
    log_count = fields.Integer(compute="compute_log_count")
    reverse_count = fields.Integer(compute="compute_log_count")

    is_boolean = fields.Boolean(compute="get_field_details")
    is_relation = fields.Boolean(compute="get_field_details")
    is_selection = fields.Boolean(compute="get_field_details")
    is_date = fields.Boolean(compute="get_field_details")
    is_datetime = fields.Boolean(compute="get_field_details")
    is_monetary = fields.Boolean(compute="get_field_details")
    is_char = fields.Boolean(compute="get_field_details")

    is_scheduled = fields.Boolean(compute="compute_scheduled_status")

    contract_state = fields.Selection(related="contract_id.state")
    contract_date_end = fields.Date('Contract Date End', related="contract_id.date_end")

    @api.onchange('employee_id')
    def _default_contract(self):
        self.contract_id = False
        contract_ids = self.env['hr.contract'].search(
            [('employee_id', '=', self.employee_id.id), ('state', 'in', ['open', 'close']),
             ('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        if len(contract_ids.filtered(lambda x: x.state == 'open')) == 1:
            self.contract_id = contract_ids.filtered(lambda x: x.state == 'open').id
        elif len(contract_ids.filtered(lambda x: x.state == 'close')) > 0:
            self.contract_id = \
            contract_ids.filtered(lambda x: x.state == 'close').sorted(key=lambda x: x.date_end, reverse=True)[0].id

    @api.onchange('contract_id')
    def _default_company(self):
        self.company_id = False
        if self.contract_id and self.contract_id.company_id:
            self.company_id = self.contract_id.company_id.id

    # Button Action

    def action_process(self) -> None:
        """
        ->action_process(): Action process button
            |->validate_management(): Validate lines
            |->process(): Applied the changes
                |->_get_field_values(): Get dict values to change from line (get_field_value)
            |->set_dates(): Limit historic management line
            |->update_state(): Update to processed state
            |
        Returns: None

        """

        to_process = self.filtered(lambda mgt: not mgt.is_scheduled)
        to_schedule = self.filtered(lambda mgt: mgt.is_scheduled)

        to_schedule.schedule_management()

        for management in to_process:
            if management.state not in ('draft', 'to_process'):
                continue
            is_cron = management.env.context.get('from_cron')
            management.validate_management()
            log_id = management.process()
            management.set_dates(log_id)
            management.sudo().update_state('processed')

            if is_cron:
                notification = _(
                    "<ul class='o_mail_thread_message_tracking'>"
                    "<li> Automatically processed:""<span class='fa fa-long-arrow-right' role='img'/>""<span> %s "
                    "</span></li>"
                    "</ul>" % management.date_init)
                management.sudo().message_post(
                    body=notification, subtype="mail.mt_note", author_id=self.env.user.partner_id.id)

    def action_draft(self):
        for management in self:
            if management.state not in ('cancelled',):  # ('cancelled', processed)
                continue
            management.update_state('draft')

    def action_cancel(self):
        for management in self:
            if management.state not in ('draft', 'processed', 'reversed'):  # ('draft', processed)
                continue
            if management.state == 'processed':
                management.action_reverse()
            management.update_state('cancelled')

    def action_cancel_schedule(self):
        for management in self:
            if management.state not in ('to_process', ):
                continue
            management.update_state('cancelled')

    # Server Action

    def action_reverse(self):
        reverse_date = fields.datetime.now()
        for management in self:
            management.validate_reverse()  # Validate management to reverse

            log_id = management.log_ids.filtered(lambda l: l.state == 'actual')[0]

            management.reverse(reverse_date, log_id)
            management.set_reverse_state(reverse_date, log_id)

            # ## Payroll correction  RQ730-RQ940 ## #
            # Payroll correction compare actual month with payroll already posted
            # If contract management was processed at 23/7/2021 and reversion happens at 15/09/2021
            # It'll found 2 payslip August-monthly and Sept-Monthly (Payslip after 23/7/2021)
            # For August-monthly, it runs a new payslip in August-monthly and compare with August-monthly already posted

            # domain = [('contract_id', '=', management.contract_id.id),
            #           ('date_to', '>', management.date_init), ('state', '=', 'done')]
            # payslips_to_correct = self.env['hr.payslip'].search(domain)
            #
            # if payslips_to_correct and management.date_init and False: payslips_run_correct =
            # payslips_to_correct.mapped('payslip_run_id') for payslip_run_correct in payslips_run_correct:
            # payslip_run_correct.with_context(management_id=management.id,
            # force_contract_id).action_compute_correction()

    # act_window actions

    def action_view_logs(self) -> Dict:
        self.ensure_one()
        this_ids = self.log_ids.ids
        name = _("Logs")
        if self.env.context.get('only_reversed', False):
            this_ids = self.log_ids.filtered(lambda l: l.state == 'reversed').ids
            name = _("Changes Reversed")
        action = self.env.ref('lt_hr_contract_management.contract_management_log_act_window').read()[0]
        form = self.env.ref('lt_hr_contract_management.contract_management_log_form_view').id
        tree = self.env.ref('lt_hr_contract_management.contract_management_log_tree_view').id
        action.update({
            'name': name,
            'domain': [('id', 'in', this_ids)],
            'views': [(tree, 'tree'), (form, 'form')]
        })
        return action

    def process_future_management(self):
        try:
            this = self.sudo()
            managements = this.search([('state', '=', 'to_process')])
            now, today = today_timezone()
            management_to_process = managements.filtered(lambda mgt: mgt.date_init and mgt.date_init <= today)

            for management in management_to_process:
                try:
                    management.with_context(from_cron=True).sudo().action_process()
                except Exception as post_msg:
                    management.post_message_channel(post_msg)
        except Exception as msg:
            _logger.debug("Exception while sending a messages channels: %s" % msg)

    # onchange methods
    @api.onchange('date_init')
    def onchange_init_date(self):
        for management in self:
            if management.date_init:
                for line in management.line_ids:
                    line.date_start = management.date_init

    @api.onchange('type_id', 'employee_id')
    def onchange_type_id(self):
        msg = None
        for management in self:
            type_id = management.type_id
            if type_id and management.contract_id:
                if management.state != 'draft':
                    raise UserError(_("The reason only can be changed in draft state"))
                if not type_id or not type_id.class_ids:
                    raise UserError(_("The measurement chosen not has reason or class defined"))
                fields_list = type_id.class_ids.mapped(lambda l: (l.id, l.field_id))

                management.create_lines(fields_list)
                management.onchange_init_date()
            elif type_id and management.employee_id and not management.contract_id:
                _msg = _("The contract must be defined to calculate the class changes")
                msg = {'warning': {'title': _("No contract"), 'message': _msg, 'type': 'notification'}}

        return msg

    # compute methods

    @api.depends('date_init')
    def compute_scheduled_status(self):
        for management in self:
            is_scheduled = False
            if management.date_init and management.date_init > today_timezone()[-1] and \
                    not management.type_id.allow_future_measurement:
                is_scheduled = True
            management.is_scheduled = is_scheduled

    def _compute_current_company(self):
        for management in self:
            management.ui_company_id = self.env.company

    def compute_log_count(self):
        for management in self:
            management.log_count = len(management.log_ids)
            management.reverse_count = len(management.log_ids.filtered(lambda l: l.state == 'reversed'))

    @api.depends('type_id')
    def get_field_details(self):
        for management in self:
            is_boolean = is_relation = is_selection = is_date = is_datetime = is_monetary = is_char = False
            if management.type_id and management.type_id.class_ids:
                field_types = management.type_id.class_ids.mapped(lambda field: field.field_id.ttype)

                if 'char' in field_types or 'text' in field_types or 'float' in field_types or 'integer' in field_types:
                    is_char = True
                if 'boolean' in field_types:
                    is_boolean = True
                if 'date' in field_types:
                    is_date = True
                if 'datetime' in field_types:
                    is_datetime = True
                if 'monetary' in field_types:
                    is_monetary = True
                if 'selection' in field_types:
                    is_selection = True
                if 'many2one' in field_types:
                    is_relation = True

            management.write({
                'is_boolean': is_boolean,
                'is_relation': is_relation,
                'is_selection': is_selection,
                'is_date': is_date,
                'is_datetime': is_datetime,
                'is_monetary': is_monetary,
                'is_char': is_char,
            })

    # custom methods

    ########################################
    # **** MEASURE CREATION LINES ******** #
    ########################################
    def create_lines(self, classes: list):
        try:
            self.ensure_one()
        except ValueError as e:
            raise ValidationError(_("Please, contact to administrator\n\n.Expected singleton: %s" % self))
        self.line_ids -= self.line_ids
        create_method = self.line_ids.new
        if self.env.context.get('force_create', False):
            create_method = self.env['contract.management.line'].create
        for id_class, field in classes:
            new_record = create_method(self._get_line(id_class, field))

    ########################################
    # ********** PROCESS METHODS ********* #
    ########################################

    def schedule_management(self):
        if not self:
            return
        for management in self:
            if management.state in ('to_process',):
                continue
            management.validate_management()
            management.update_state('to_process')

    def post_message_channel(self, msg):
        user = self.env['res.users'].sudo().browse(SUPERUSER_ID)
        poster = self.sudo().env.ref('lt_hr_contract_management.channel_retirement_management',
                                     raise_if_not_found=False)

        msg_channel = _('<div class="o_mail_notification">Future contract management: '
                        '<a href="#" class="o_channel_redirect" data-oe-id="%s">#%s</a> '
                        'has failed.<br/> Error: %s</div>') % (self.id, self.name, msg, )
        if not (poster and poster.exists()):
            if not user.exists():
                return False
        try:
            poster.message_post(body=msg_channel, type="notification", subtype='mt_comment', )
        except Exception as e:
            _logger.debug("Exception while sending a messages channels: %s" % e)

    def process(self) -> ContractManagementLog:
        try:
            self.ensure_one()
        except ValueError as e:
            raise ValidationError(_("Please, contact to administrator\n\n.Expected singleton: %s" % self))

        fields_values, field_list, is_analytic_changed = self._get_field_values()
        log_id = self.update_contract_management_log(field_list)
        self.contract_id.with_context(hr_work_entry_no_check=True).write(fields_values)

        self.env["contract.management.log.line"].create_log_line(
            'trial_date_end', self.contract_id, self, 'write_line_dates',
            log_id=log_id, kwargs={'with_sudo': True})

        return log_id

    def config_analytic_distribution(self, log_id: ContractManagementLog, analytic_value: int):
        """
        Limit analytic distribution with the old analytic account at the date of management.
        Create the new one analytic distribution based on the new analytic account.

        Args:
            log_id:
            analytic_value:

        Returns:

        """

        dist_object = self.env['hr.analytic.distribution.line']
        log_object = self.env["contract.management.log.line"]

        old_analytic_id, new_analytic_id = self._get_analytic_values('analytic_account_id', analytic_value)

        domain = [('type', '=', 'main'), ('analytic_account_id', '=', old_analytic_id.id),
                  ('date_end', '=', False), ('contract_id', '=', self.contract_id.id)]

        date_to_limit = self.date_init

        # Update limiting at management date for the main distribution

        main_distributions = dist_object.search(domain)
        for distribution in main_distributions:

            log_object.create_log_line('date_end', distribution, self, 'write_line_dates', log_id=log_id,
                                       kwargs={'with_sudo': True})
            log_object.create_log_line('type', distribution, self, 'write_line_char', log_id=log_id,
                                       kwargs={'with_sudo': True})
            date_limits = self.limit_distribution(date_to_limit)
            distribution.write({'date_end': date_limits})

            if not self.type_id.is_employer_replacement:
                distribution.write({'type': 'distribution'})

        ''' Create new main account line '''
        new_line = self.prepare_distribution_line(date_to_limit, new_analytic_id)
        distribution_line_id = dist_object.sudo().create(new_line)

        if distribution_line_id:
            log_object.create_log_line('id', distribution_line_id, self, 'delete_many2one', log_id=log_id,
                                       kwargs={'with_sudo': True})

        return distribution_line_id

    def prepare_distribution_line(self, date: fields.date, analytic_account_id) -> Dict:
        tags = analytic_account_id.account_analytic_tag_ids
        return {
            'company_id': self.company_id.id,
            'employee_id': self.employee_id.id,
            'contract_id': self.contract_id.id,
            'analytic_account_id': analytic_account_id.id if analytic_account_id else False,
            'tag_ids': tags.ids if tags else False,
            'percentage': 100,
            'days': 0,
            'date_start': date,
            'type': 'main',
            'state': 'approved',
        }

    def _get_field_values(self) -> Tuple[Dict, List[IrModelFields, ], bool]:
        lines = self.line_ids
        field_list = []
        values_to_update = {}

        is_analytic_changed = None
        analytic_field = 'analytic_account_id'

        for line in lines:  # contract.management.line
            field_name, value, field = line.get_field_value()
            values_to_update.update({field_name: value})
            if field_name == analytic_field:
                old_value, new_value = self._get_analytic_values(analytic_field, value)

                # TODO Uncomment after going live, it is for the massive loading of analytical accounts.
                if old_value != new_value:
                    is_analytic_changed = value
                else:
                    raise UserError(_('It is not possible to execute a change of contract by the analytical account, '
                                      'I select as change the same analytical account for the contract %s' % self.contract_id.name))

            field_list.append(field)

            if self.type_id.remove_date_end_contract:
                field_name_end_contract = self.env['ir.model.fields'].search([('name', 'in', ('last_date_end', 'date_end'))]).filtered(lambda x: x.model_id.model == 'hr.contract')
                for field_contract in field_name_end_contract:
                    if field_contract.name == 'last_date_end':
                        values_to_update.update({field_contract.name: self.contract_id.date_end})
                        field_list.append(field_contract)
                    elif field_contract.name == 'date_end':
                        values_to_update.update({field_contract.name: False})
                        field_list.append(field_contract)

        return values_to_update, field_list, is_analytic_changed

    def update_contract_management_log(self, field_list: List[IrModelFields,]) -> ContractManagementLog:
        date_to_updated = fields.datetime.now()
        lines_to_create = []

        for field in field_list:
            method = None
            value = getattr(self.contract_id, field.name)
            _type = field.ttype

            if _type == 'many2one' and value:
                value = value.id

            if _type in ('char', 'selection', 'text'):
                method = 'write_line_char'
            elif _type in ('date', 'datetime',):
                method = 'write_line_dates'
            elif _type in ('float', 'integer', 'monetary',):
                method = 'write_line_number'

            line = {
                'field_id': field.id,
                'management_id': self.id,
                'state': 'actual',
                'model_to_affect': 'hr.contract',
                'id_to_affect': self.contract_id.id,
                'value': str(value),
                'method': method if method else 'write_line_%s' % _type,
                'date': date_to_updated,
            }
            lines_to_create.append(line)

        # hook to append lines to create
        lines_to_create = self.append_lines(lines_to_create)

        log_ids = self.env['contract.management.log'].create({
            'name': self.name,
            'date': date_to_updated,
            'state': 'actual',
            'management_id': self.id,
            'contract_id': self.contract_id.id,
            'line_ids': [(0, 0, line) for line in lines_to_create]
        })

        return log_ids

    def set_dates(self, log_id: ContractManagementLog):
        for management in self:
            for line in management.line_ids:
                line.set_date(log_id)

    def get_sequence(self):
        company = self.actual_company_id or self.env.company
        ir_sequence = self.env['ir.sequence']
        sequence_id = ir_sequence.search([('code', '=', 'contract.management'),
                                          ('company_id', '=', company.id)])
        return sequence_id, company

    def _get_line(self, id_class: int, field) -> dict:
        basic_line = {
            'class_id': id_class,
            'field_id': field.id,
            'model_relation': field.relation,
            'management_id': self.id,
            'employee_id': self.employee_id.id,
            'contract_id': self.contract_id.id,
            'company_id': self.company_id.id,
        }
        if field.ttype == 'many2one' and field.relation:
            field_value = getattr(self.contract_id, field.name)
            basic_line.update({
                'type_relation_id': '%s,%s' % (field.relation, field_value.id),
            })

        return basic_line

    def update_state(self, state):
        for management in self:
            management.write({'state': state})
            if management.line_ids:
                management.line_ids.write({'state': state})

    ########################################
    # ********** REVERSE METHODS ********* #
    ########################################

    def reverse(self, reverse_date: fields.Date, log_id: ContractManagementLog):

        try:
            self.ensure_one()
        except ValueError as e:
            raise ValidationError(_("Please, contact to administrator\n\n.Expected singleton: %s" % self))

        pass

        lines_to_reverse = log_id.line_ids.filtered(lambda l: l.state == 'actual')

        for reverse_line in lines_to_reverse:
            reverse_line.make_reverse(reverse_date)

    def set_reverse_state(self, reverse_date, log_id) -> None:
        for management in self:
            management.write({'state': 'reversed', 'reversed_date': reverse_date})
            management.line_ids.set_reverse_state(reverse_date)
            log_id.set_reverse(reverse_date)

    def _get_analytic_values(self, analytic_field, value):
        old_value = getattr(self.sudo().contract_id, analytic_field)
        new_value = self.env['account.analytic.account'].sudo().browse(value)
        return old_value, new_value

    # Validation methods

    def validate_management(self):
        for management in self:
            lines = management.line_ids
            if not management.line_ids:
                raise UserError(_("Not is possible process the changes without changes"))
            lines.validate_lines()

    def validate_reverse(self) -> bool:
        not_allowed = []
        for management in self:
            if management.state not in ('processed',):
                not_allowed.append('%s - %s' % (management.name, management.state))
        if not_allowed:
            str_names = '\n\t'.join(not_allowed)
            raise UserError(
                _("Reverse operation not allowed, "
                  "for this documents\n\n\t%s\n\nYou can reverse only in processed state.") % str_names)
        return True

    # model methods

    @api.model
    def view_init(self, fields_list):
        super(ContractManagement, self).view_init(fields_list)

        sequence_id, company = self.get_sequence()

        if len(sequence_id) > 1:
            msg = _(
                "Multiple sequence found for contract.management in this company %s. Contact with the administrator")
            raise ValidationError(msg % company.name)

        if not sequence_id:
            self.env['ir.sequence'].create({
                'number_next': 1,
                'company_id': company.id,
                'padding': 5,
                'number_increment': 1,
                'code': 'contract.management',
                'implementation': 'standard',
                'prefix': 'GCC',
                'name': _('Contract Change Management %s') % company.name,
            })

    @api.model
    def create(self, val_list):
        defaults = self.default_get(['name', ])
        if not val_list.get('name', '') and defaults.get('name', '') == '':
            sequence_id, company = self.get_sequence()
            name = sequence_id.next_by_id()
            val_list.update({
                'name': name
            })

        return super(ContractManagement, self).create(val_list)

    @api.model
    def append_lines(self, lines: list) -> List:
        # OVERRIDE
        return lines + []

    @api.model
    def limit_distribution(self, date: fields.date):
        return date - relativedelta(days=1)

    def name_get(self):
        return [(management.id, management.name or _('Draft Contract Change Management')) for management in self]

    def action_archive(self):
        for management in self:
            if management.state in ('processed',):
                raise UserError(_("Not possible archive Contract Change Management in processed state"))
        return super(ContractManagement, self).action_archive()

    def unlink(self):
        not_allowed = []
        for management in self:
            if management.state not in ('draft',):
                not_allowed.append('%s - %s' % (management.name, management.state))
        if not_allowed:
            str_names = '\n\t'.join(not_allowed)
            raise UserError(
                _("Delete operation not allowed, for this documents\n\n\t%s\n\nYou can delete only in draft state.")
                % str_names)
        return super(ContractManagement, self).unlink()
