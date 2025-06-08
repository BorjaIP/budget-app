from pathlib import Path
from typing import List

import pandas as pd
import reflex as rx

from dashboard.expenses.model import Item
from dashboard.utils.file_reader import FileReader
from dashboard.utils.file_processor import file_processor
from dashboard.database.operations import db_manager


class TableState(rx.State):

    items: List[Item] = []
    items_list: List[str] = []

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    total_items: int = 0
    offset: int = 0
    limit: int = 12  # Number of rows per page
    
    # File upload state
    upload_status: str = ""
    is_uploading: bool = False
    uploaded_files: List[str] = []

    @rx.var(cache=True)
    def filtered_sorted_items(self) -> List[Item]:
        items = self.items

        # Filter items based on selected item
        if self.sort_value:
            if self.sort_value in ["amount"]:
                items = sorted(
                    items,
                    key=lambda item: float(getattr(item, self.sort_value)),
                    reverse=self.sort_reverse,
                )
            else:
                items = sorted(
                    items,
                    key=lambda item: str(getattr(item, self.sort_value)).lower(),
                    reverse=self.sort_reverse,
                )

        # Filter items based on search value
        if self.search_value:
            search_value = self.search_value.lower()
            items = [
                item
                for item in items
                if any(
                    search_value in str(getattr(item, attr)).lower() for attr in self.items_list
                )
            ]

        return items

    @rx.var(cache=True)
    def get_item_list(self) -> list[str]:
        return self.items_list

    @rx.var(cache=True)
    def page_number(self) -> int:
        return (self.offset // self.limit) + 1

    @rx.var(cache=True)
    def total_pages(self) -> int:
        return (self.total_items // self.limit) + (1 if self.total_items % self.limit else 1)

    @rx.var(cache=True, initial_value=[])
    def get_current_page(self) -> list[Item]:
        start_index = self.offset
        end_index = start_index + self.limit
        return self.filtered_sorted_items[start_index:end_index]

    def prev_page(self):
        if self.page_number > 1:
            self.offset -= self.limit

    def next_page(self):
        if self.page_number < self.total_pages:
            self.offset += self.limit

    def first_page(self):
        self.offset = 0

    def last_page(self):
        self.offset = (self.total_pages - 1) * self.limit

    # def extract_category(self):
    #     for exp in self.items:
    #         category = asyncio.run(query_llm(PROMPT, exp.concept))
    #         exp.category = category

    def load_entries_from_database(self):
        """Load entries from database"""
        try:
            # Get all expenses from database
            db_expenses = db_manager.get_all_expenses()
            
            if db_expenses:
                # Convert database models to Item objects for compatibility
                items = []
                for expense in db_expenses:
                    item = Item(
                        operation_date=expense.operation_date,
                        value_date=expense.value_date,
                        concept=expense.concept,
                        amount=expense.amount,
                        salary=expense.salary,
                        category=expense.category
                    )
                    items.append(item)
                
                self.items = items  # Already ordered by created_at desc
                self.total_items = len(self.items)
                self.items_list = list(Item.__annotations__.keys())
                print(f"Successfully loaded {len(self.items)} entries from database")
            else:
                print("No data found in database")
                self.items = []
                self.total_items = 0
        except Exception as e:
            print(f"Error loading entries from database: {e}")
            self.items = []
            self.total_items = 0
    
    # Keep old method for backward compatibility, but redirect to database
    def load_entries(self, filepath: str = ""):
        """Load entries (redirects to database load)"""
        self.load_entries_from_database()

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Handle file upload using Reflex pattern"""
        if not files:
            self.upload_status = "No file selected"
            return
        
        self.is_uploading = True
        self.upload_status = "Processing file..."
        
        try:
            for file in files:
                # Check if filename exists
                if not file.filename:
                    self.upload_status = "❌ Invalid file"
                    continue
                
                # Check file extension
                if not file.filename.lower().endswith(('.xls', '.xlsx')):
                    self.upload_status = "❌ Only Excel files (.xls, .xlsx) are allowed"
                    continue
                
                # Save file to Reflex upload directory
                upload_data = await file.read()
                outfile = rx.get_upload_dir() / file.filename
                
                # Ensure upload directory exists
                outfile.parent.mkdir(parents=True, exist_ok=True)
                
                # Write file to upload directory
                with outfile.open("wb") as file_object:
                    file_object.write(upload_data)
                
                # Process the uploaded file from the upload directory
                result = file_processor.process_excel_file(str(outfile), replace_existing=True)
                
                if result["status"] == "success":
                    self.upload_status = f"✅ {result['message']}"
                    # Reload data from database
                    self.load_entries_from_database()
                    print(f"Upload successful: {result['count']} records processed")
                    
                    # Clean up uploaded file after processing
                    try:
                        outfile.unlink()
                    except:
                        pass  # File cleanup not critical
                else:
                    self.upload_status = f"❌ {result['message']}"
                    print(f"Upload failed: {result['message']}")
                
        except Exception as e:
            self.upload_status = f"❌ Upload failed: {str(e)}"
            print(f"Upload error: {e}")
        finally:
            self.is_uploading = False
    
    def clear_upload_status(self):
        """Clear upload status message"""
        self.upload_status = ""
    
    def trigger_upload(self):
        """Trigger file upload processing"""
        return TableState.handle_upload(rx.upload_files(upload_id="upload-excel"))
    
    def simple_upload_trigger(self):
        """Simple upload trigger without files parameter"""
        self.upload_status = "Please select files first, then click to process"
    
    @rx.var
    def get_upload_stats(self) -> str:
        """Get upload statistics"""
        try:
            total_expenses = len(db_manager.get_all_expenses())
            file_sources = db_manager.get_unique_file_sources()
            return f"Database: {total_expenses} records from {len(file_sources)} files"
        except Exception:
            return "Database: No data"
    
    def get_database_files(self):
        """Get list of unique file sources in database"""
        try:
            self.uploaded_files = db_manager.get_unique_file_sources()
        except Exception as e:
            print(f"Error getting database files: {e}")
            self.uploaded_files = []

    def toggle_sort(self):
        self.sort_reverse = not self.sort_reverse
        self.load_entries_from_database()
