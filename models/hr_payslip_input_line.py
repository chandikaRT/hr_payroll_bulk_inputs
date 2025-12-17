from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrPayslipInputLine(models.Model):
    _name = 'hr.payslip.input.line'
    _description = 'Bulk Payslip Input Line'
    _rec_name = 'employee_id'

    bulk_input_id = fields.Many2one(
        'hr.payslip.bulk.input',
        string='Bulk Input',
        required=True,
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )
    amount = fields.Float(
        string='Amount',
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='bulk_input_id.input_type_id.company_id',
        store=True
    )

    _sql_constraints = [
        ('unique_employee_input',
         'UNIQUE(bulk_input_id, employee_id)',
         'Employee can only appear once per bulk input entry!')
    ]

    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount < 0:
                raise ValidationError(_("Amount cannot be negative!"))