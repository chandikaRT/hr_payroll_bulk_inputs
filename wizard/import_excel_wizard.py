import base64
import openpyxl
from io import BytesIO
from odoo import models, fields, api
from odoo.exceptions import UserError


class ImportExcelWizard(models.TransientModel):
    _name = 'hr.payslip.input.import.wizard'
    _description = 'Import Payslip Inputs from Excel'

    bulk_input_id = fields.Many2one(
        'hr.payslip.bulk.input',
        string='Bulk Input Record',
        required=True
    )
    excel_file = fields.Binary(
        string='Excel File',
        required=True
    )
    filename = fields.Char(string='File Name')

    def action_import(self):
        self.ensure_one()
        
        if not self.excel_file:
            raise UserError(_("Please select an Excel file to import."))
        
        try:
            # Decode the file
            data = base64.b64decode(self.excel_file)
            wb = openpyxl.load_workbook(filename=BytesIO(data))
            sheet = wb.active
            
            # Get header row to find columns
            headers = {cell.value: idx for idx, cell in enumerate(sheet[1], start=1)}
            
            required_columns = ['Employee', 'Amount']
            for col in required_columns:
                if col not in headers:
                    raise UserError(_(f"Missing required column: '{col}'"))
            
            # Process rows
            successful = 0
            errors = []
            Employee = self.env['hr.employee']
            InputLine = self.env['hr.payslip.input.line']
            
            # Clear existing lines for this bulk input
            self.bulk_input_id.line_ids.unlink()
            
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    employee_name = row[headers['Employee'] - 1]
                    amount = row[headers['Amount'] - 1]
                    
                    if not employee_name or not amount:
                        errors.append(f"Row {row_idx}: Missing employee or amount")
                        continue
                    
                    # Find employee (exact match or search)
                    employee = Employee.search([('name', '=', employee_name)], limit=1)
                    if not employee:
                        # Try fuzzy search
                        employee = Employee.search([('name', 'ilike', employee_name)], limit=1)
                    
                    if not employee:
                        errors.append(f"Row {row_idx}: Employee '{employee_name}' not found")
                        continue
                    
                    # Create input line
                    InputLine.create({
                        'bulk_input_id': self.bulk_input_id.id,
                        'employee_id': employee.id,
                        'amount': float(amount),
                    })
                    successful += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_idx}: {str(e)}")
            
            # Show result
            message = f"Successfully imported {successful} records."
            if errors:
                message += f"\n\nErrors:\n" + "\n".join(errors[:10])  # Show first 10 errors
                if len(errors) > 10:
                    message += f"\n... and {len(errors) - 10} more errors."
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Import Result',
                    'message': message,
                    'type': 'info' if not errors else 'warning',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            raise UserError(_(f"Error reading Excel file: {str(e)}"))