import os
import shutil
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .file_reader import FileReader
from ..database.operations import db_manager
from ..database.models import ExpenseCreate


class FileProcessor:
    """Process uploaded Excel files and store in database"""
    
    def __init__(self, temp_folder: str = "temp_uploads"):
        self.temp_folder = Path(temp_folder)
        self.temp_folder.mkdir(exist_ok=True)
        self.file_reader = FileReader()
    
    def save_uploaded_file(self, uploaded_file_data: bytes, filename: str) -> str:
        """Save uploaded file to temporary folder"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{filename}"
        file_path = self.temp_folder / safe_filename
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file_data)
        
        return str(file_path)
    
    def process_excel_file(self, file_path: str, replace_existing: bool = False) -> dict:
        """
        Process Excel file and store in database
        
        Returns:
            dict with status, message, and count of processed records
        """
        try:
            # Extract filename for database reference
            filename = Path(file_path).name
            
            # Check if file with same name already exists in database
            existing_expenses = db_manager.get_expenses_by_file(filename)
            if existing_expenses and not replace_existing:
                return {
                    "status": "warning",
                    "message": f"File '{filename}' already exists in database. Use replace option to update.",
                    "count": 0
                }
            
            # Read and process Excel file
            records = self.file_reader.read_file_to_records(file_path)
            
            if not records:
                return {
                    "status": "error",
                    "message": "No valid data found in Excel file",
                    "count": 0
                }
            
            # Convert records to ExpenseCreate models
            expenses = []
            for record in records:
                try:
                    expense = ExpenseCreate(
                        operation_date=str(record.get('operation_date', '')),
                        value_date=str(record.get('value_date', '')),
                        concept=str(record.get('concept', '')),
                        amount=str(record.get('amount', '')),
                        salary=str(record.get('salary', '')),
                        category=record.get('category', None)
                    )
                    expenses.append(expense)
                except Exception as e:
                    print(f"Skipping invalid record: {e}")
                    continue
            
            if not expenses:
                return {
                    "status": "error",
                    "message": "No valid expense records could be created",
                    "count": 0
                }
            
            # Replace existing data if requested
            if existing_expenses and replace_existing:
                deleted_count = db_manager.delete_expenses_by_file(filename)
                print(f"Replaced {deleted_count} existing records")
            
            # Insert into database
            inserted_count = db_manager.insert_expenses(expenses, filename)
            
            # Clean up temp file
            try:
                os.remove(file_path)
            except OSError:
                pass  # File cleanup not critical
            
            return {
                "status": "success",
                "message": f"Successfully processed {inserted_count} records from '{filename}'",
                "count": inserted_count
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error processing file: {str(e)}",
                "count": 0
            }
    
    def get_uploaded_files(self) -> List[str]:
        """Get list of files in temp folder"""
        return [f.name for f in self.temp_folder.iterdir() if f.is_file()]
    
    def cleanup_temp_folder(self):
        """Clean up temporary folder"""
        if self.temp_folder.exists():
            shutil.rmtree(self.temp_folder)
            self.temp_folder.mkdir(exist_ok=True)


# Global file processor instance
file_processor = FileProcessor() 