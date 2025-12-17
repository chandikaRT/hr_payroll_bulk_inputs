from odoo import models, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_employee(self):
        res = super(HrPayslip, self).onchange_employee()
        
        if self.employee_id and self.date_from and self.date_to:
            # Get the month of the payslip
            month_start = self.date_from.replace(day=1)
            
            # Find confirmed bulk inputs for this employee and month
            bulk_lines = self.env['hr.payslip.input.line'].search([
                ('employee_id', '=', self.employee_id.id),
                ('bulk_input_id.date', '=', month_start),
                ('bulk_input_id.state', '=', 'confirmed')
            ])
            
            # Prepare input lines for payslip
            input_lines = []
            existing_codes = {line.code for line in self.input_line_ids}
            
            for line in bulk_lines:
                input_type = line.bulk_input_id.input_type_id
                
                # Skip if already added
                if input_type.code in existing_codes:
                    continue
                
                input_lines.append((0, 0, {
                    'input_type_id': input_type.id,
                    'amount': line.amount,
                    'name': line.bulk_input_id.name,
                }))
            
            if input_lines:
                self.input_line_ids = input_lines
        
        return res

    def compute_sheet(self):
        """Override to ensure bulk inputs are included"""
        for payslip in self:
            # Re-apply bulk inputs before computation
            month_start = payslip.date_from.replace(day=1)
            
            # Remove auto-populated bulk inputs to avoid duplicates
            bulk_input_types = payslip.env['hr.payslip.bulk.input'].search([
                ('date', '=', month_start),
                ('state', '=', 'confirmed')
            ]).mapped('input_type_id').ids
            
            payslip.input_line_ids = payslip.input_line_ids.filtered(
                lambda x: x.input_type_id.id not in bulk_input_types
            )
            
            # Reapply fresh
            bulk_lines = payslip.env['hr.payslip.input.line'].search([
                ('employee_id', '=', payslip.employee_id.id),
                ('bulk_input_id.date', '=', month_start),
                ('bulk_input_id.state', '=', 'confirmed')
            ])
            
            for line in bulk_lines:
                payslip.input_line_ids = [(0, 0, {
                    'input_type_id': line.bulk_input_id.input_type_id.id,
                    'amount': line.amount,
                    'name': line.bulk_input_id.name,
                })]
        
        return super(HrPayslip, self).compute_sheet()