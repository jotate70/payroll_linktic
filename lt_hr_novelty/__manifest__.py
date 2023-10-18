{
    'name': 'Novedades de Nómina - LinkTic SAS',
    'version': '1.0',
    'summary': 'Gestión de novedades para la nómina de LinkTic SAS',
    'description': """
        Este módulo permite gestionar las novedades de nómina para la empresa LinkTic SAS.
        Permite registrar y procesar diversas novedades que afectan el cálculo de la nómina.
    """,
    'author': 'Diego Felipe Torres Reyes',
    'license': 'AGPL-3',
    'website': 'https://www.linktic.com',
    'category': 'Human Resources',
    'depends': ['base', 'om_hr_payroll'],  # Dependencias de otros módulos
    'data': [
        # Data
        'data/hr_novelty_category_data.xml',
        'data/hr_novelty_type_data.xml',
        'data/ir_sequence.xml',
        # Security
        'security/ir.model.access.csv',  # Archivo de seguridad
        # Views
        'views/menu.xml',  # Vistas XML
        'views/hr_novelty_category_view.xml',
        'views/hr_novelty_type_view.xml',
        'views/hr_novelty_view.xml',
        # 'views/hr_payslip_view.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
