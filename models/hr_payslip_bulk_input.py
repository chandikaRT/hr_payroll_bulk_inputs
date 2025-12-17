from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrPayslipBulkInput(models.Model):
    _name = 'hr.payslip.bulk.input'
    _description = 'Bulk Payslip Inputs'
    _order = 'date DESC'

    name = fields.Char(
        string='Description',
        required=True,
        help="E.g., 'January 2025 Transport Deductions'"
    )
    date = fields.Date(
        string='Effective Month',
        required=True,
        default=fields.Date.today,
        help="Select the month/year for these inputs"
    )
    input_type_id = fields.Many2one(
        'hr.payslip.input.type',
        string='Input Type',
        required=True,
        help="Select the payslip input type (must be linked to salary rule)"
    )
    line_ids = fields.One2many(
        'hr.payslip.input.line',
        'bulk_input_id',
        string='Employee Inputs'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft')
    total_employees = fields.Integer(
        string='Total Employees',
        compute='_compute_totals',
        store=True
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_totals',
        store=True
    )
    # Add currency for display
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        store=True
    )

    @api.depends('line_ids', 'line_ids.amount')
    def _compute_totals(self):
        for record in self:
            record.total_employees = len(record.line_ids)
            record.total_amount = sum(line.amount for line in record.line_ids)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    @api.constrains('date')
    def _check_date(self):
        for record in self:
            # Ensure date is first day of month for consistency
            if record.date.day != 1:
                record.date = record.date.replace(day=1)

    def _get_input_key(self):
        """Generate unique key for payslip input matching"""
        return f"{self.input_type_id.code}_{self.date.strftime('%Y_%m')}"