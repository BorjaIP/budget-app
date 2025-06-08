import os
from pathlib import Path
from typing import List, Optional
from sqlmodel import SQLModel, create_engine, Session, select, desc
from .models import Expense, ExpenseCreate


class DatabaseManager:
    """Database manager for expense data"""
    
    def __init__(self, db_path: str = "expenses.db"):
        self.db_path = db_path
        # Create database directory if it doesn't exist
        db_dir = Path(db_path).parent
        db_dir.mkdir(exist_ok=True)
        
        # Create engine and tables
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.create_tables()
    
    def create_tables(self):
        """Create database tables"""
        SQLModel.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return Session(self.engine)
    
    def insert_expenses(self, expenses: List[ExpenseCreate], file_source: Optional[str] = None) -> int:
        """Insert multiple expenses into database"""
        with self.get_session() as session:
            db_expenses = []
            for expense_data in expenses:
                # Add file source to each expense
                expense_dict = expense_data.dict()
                expense_dict['file_source'] = file_source or "unknown"
                db_expense = Expense(**expense_dict)
                db_expenses.append(db_expense)
            
            session.add_all(db_expenses)
            session.commit()
            return len(db_expenses)
    
    def get_all_expenses(self, limit: Optional[int] = None) -> List[Expense]:
        """Get all expenses from database"""
        with self.get_session() as session:
            statement = select(Expense).order_by(desc(Expense.created_at))
            if limit:
                statement = statement.limit(limit)
            
            expenses = session.exec(statement).all()
            return list(expenses)
    
    def get_expenses_by_file(self, file_source: str) -> List[Expense]:
        """Get expenses from specific file"""
        with self.get_session() as session:
            statement = select(Expense).where(Expense.file_source == file_source)
            expenses = session.exec(statement).all()
            return list(expenses)
    
    def delete_expenses_by_file(self, file_source: str) -> int:
        """Delete expenses from specific file"""
        with self.get_session() as session:
            statement = select(Expense).where(Expense.file_source == file_source)
            expenses = session.exec(statement).all()
            count = len(expenses)
            
            for expense in expenses:
                session.delete(expense)
            
            session.commit()
            return count
    
    def clear_all_expenses(self) -> int:
        """Clear all expenses from database"""
        with self.get_session() as session:
            statement = select(Expense)
            expenses = session.exec(statement).all()
            count = len(expenses)
            
            for expense in expenses:
                session.delete(expense)
            
            session.commit()
            return count
    
    def get_unique_file_sources(self) -> List[str]:
        """Get list of unique file sources"""
        with self.get_session() as session:
            statement = select(Expense.file_source).distinct()
            file_sources = session.exec(statement).all()
            return [fs for fs in file_sources if fs is not None]


# Global database manager instance
db_manager = DatabaseManager() 