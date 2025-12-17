import base64
import openpyxl
from io import BytesIO
from odoo import models, fields, api
from odoo.exceptions import UserError


class ImportExcelWizard(models.TransientModel):
    _name = 'hr.payslip.input.import.wizard'
    _description = 'Import Payslip Inputs from Excel'

    date = fields.Date(
        string='Target Month',
        required=True,
        default=fields.Date.today(),
        help="Select the month/year for these inputs (day will be set to 1st)"
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
            headers = {}
            for idx, cell in enumerate(sheet[1], start=1):
                if cell.value:
                    headers[cell.value.strip()] = idx
            
            required_columns = ['Employee', 'Input Type', 'Amount']
            for col in required_columns:
                if col not in headers:
                    raise UserError(_(f"Missing required column: '{col}'"))
            
            # Normalize date to first day of month
            target_date = self.date.replace(day=1)
            
            # Process rows and group by input type
            Employee = self.env['hr.employee']
            InputType = self.env['hr.payslip.input.type']
            BulkInput = self.env['hr.payslip.bulk.input']
            InputLine = self.env['hr.payslip.input.line']
            
            # Dictionary to hold lines grouped by input type
            input_type_data = {}
            errors = []
            
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                try:
                    employee_name = row[headers['Employee'] - 1] if row[headers['Employee'] - 1] else None
                    input_type_name = row[headers['Input Type'] - 1] if row[headers['Input Type'] - 1] else None
                    amount = row[headers['Amount'] - 1] if row[headers['Amount'] - 1] else None
                    
                    if not employee_name or not input_type_name or amount is None:
                        errors.append(f"Row {row_idx}: Missing employee, input type, or amount")
                        continue
                    
                    # Find employee
                    employee = Employee.search([('name', '=', employee_name)], limit=1)
                    if not employee:
                        employee = Employee.search([('name', 'ilike', employee_name)], limit=1)
                    
                    if not employee:
                        errors.append(f"Row {row_idx}: Employee '{employee_name}' not found")
                        continue
                    
                    # Find input type (by name or code)
                    input_type = InputType.search([
                        '|', ('name', '=', input_type_name),
                        ('code', '=', input_type_name)
                    ], limit=1)
                    
                    if not input_type:
                        errors.append(f"Row {row_idx}: Input Type '{input_type_name}' not found")
                        continue
                    
                    if not input_type.code:
                        errors.append(f"Row {row_idx}: Input Type '{input_type_name}' has no code (must be linked to salary rule)")
                        continue
                    
                    # Group by input type
                    if input_type.id not in input_type_data:
                        input_type_data[input_type.id] = []
                    
                    input_type_data[input_type.id].append({
                        'employee_id': employee.id,
                        'amount': float(amount)
                    })
                    
                except Exception as e:
                    errors.append(f"Row {row_idx}: {str(e)}")
            
            # Create or update bulk input records for each input type
            successful = 0
            for input_type_id, lines in input_type_data.items():
                input_type = InputType.browse(input_type_id)
                
                # Find or create bulk input record for this input type and month
                bulk_input = BulkInput.search([
                    ('date', '=', target_date),
                    ('input_type_id', '=', input_type_id),
                    ('state', 'in', ['draft', 'confirmed'])
                ], limit=1)
                
                if not bulk_input:
                    bulk_input = BulkInput.create({
                        'name': f"{target_date.strftime('%B %Y')} - {input_type.name}",
                        'date': target_date,
                        'input_type_id': input_type_id,
                        'state': 'draft'
                    })
                
                # Clear existing lines for this bulk input
                bulk_input.line_ids.unlink()
                
                # Create new lines
                for line_data in lines:
                    InputLine.create({
                        'bulk_input_id': bulk_input.id,
                        **line_data
                    })
                    successful += 1
            
            # Show result
            message = f"Successfully imported {successful} records for {len(input_type_data)} input types."
            if errors:
                message += f"\n\nErrors:\n" + "\n".join(errors[:10])
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