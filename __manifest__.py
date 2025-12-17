{
    'name': 'Bulk Payroll Inputs Manager',
    'version': '17.0',
    'category': 'Human Resources/Payroll',
    'author': 'Chandika Rathnayake',
    'summary': 'Manage bulk payroll inputs for multiple employees with Excel import',
    'description': """
        This module allows HR managers to:
        - Create bulk input entries for multiple employees for a specific month
        - Import inputs from Excel files
        - Automatically populate payslip Other Inputs tab
        - Link with Odoo standard hr.payslip.input.type
    """,
    'depends': [
        'hr',
        'hr_payroll',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/hr_payslip_bulk_input_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}