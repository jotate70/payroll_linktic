{
    'name': 'Gestión de Novedades de Contrato - LinkTic SAS',
    'version': '1.0',
    'summary': 'Gestión de novedades de contrato para la nómina de LinkTic SAS',
    'description': """
        Este módulo permite gestionar las novedades de contrato de nómina para la empresa LinkTic SAS.
        Permite registrar y procesar diversas novedades de contrato que afectan el cálculo de la nómina.
    """,
    'author': 'Diego Felipe Torres Reyes',
    'license': 'AGPL-3',
    'website': 'https://www.linktic.com',
    'category': 'Human Resources',
    'depends': ['base', 'hr_contract', 'hr'],  # Dependencias de otros módulos
    'data': [
        # Security
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        # Views
        # 'views/widget_template.xml',
        'views/contract_management_setting.xml',
        'views/contract_management.xml',
        'views/contract_management_line.xml',
        'views/contract_management_log.xml',
        'views/hr_contract_view.xml',
        'views/menu.xml',
        # Data
        'data/contract_management_class_data.xml',
        'data/contract_management_type_data.xml',
        'data/contract_management_reason_data.xml',
        'data/mail_channel_data.xml',
        'data/ir_cron_data.xml',
        'data/ir_sequence.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'lt_hr_contract_management/static/src/js/hr_contract_reference.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
