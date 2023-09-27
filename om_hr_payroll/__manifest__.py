# -*- coding:utf-8 -*-
{
    'name': 'Odoo 15 HR Payroll',
    'category': 'Generic Modules/Human Resources',
    'version': '15.0.4.0.0',
    'sequence': 1,
    'author': 'Odoo Mates, Odoo SA',
    'summary': 'Payroll For Odoo 15 Community Edition',
    'live_test_url': 'https://www.youtube.com/watch?v=0kaHMTtn7oY',
    'description': "Odoo 15 Payroll, Payroll Odoo 15, Odoo Community Payroll",
    'website': 'https://www.odoomates.tech',
    'license': 'LGPL-3',
    'depends': [
        'mail',
        'hr_contract',
        'hr_holidays',
    ],
    'data': [
        # Security
        'security/hr_payroll_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/hr_payroll_sequence.xml',
        'data/hr_payroll_category.xml',
        'data/hr_payroll_data.xml',
        'data/hr_payment_frequency.xml',
        'data/mail_template.xml',
        # Wizard
        'wizard/hr_payroll_payslips_by_employees_views.xml',
        'wizard/hr_payroll_contribution_register_report_views.xml',
        'wizard/generate_payroll_period.xml',
        # Views
        'views/hr_contract_type_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_payment_frequency_views.xml',
        'views/hr_payroll_period_views.xml',
        'views/hr_payroll_report.xml',
        'views/res_config_settings_views.xml',
        'views/report_contribution_register_templates.xml',
        'views/report_payslip_templates.xml',
        'views/report_payslip_details_templates.xml',
        'views/hr_contract_history_views.xml',
        'views/hr_leave_type_view.xml',
    ],
    'assets': {
        'web.assets_qweb': [
            'om_hr_payroll/static/src/xml/base.xml',
        ],
        'web.assets_backend': [
            'om_hr_payroll/static/src/js/generate_periods.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'application': True,
}

