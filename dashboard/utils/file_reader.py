from pathlib import Path
from typing import List, Dict, Any, Literal
import pandas as pd


class FileReader:
    """Class to handle reading different Excel file formats and converting to expense data"""
    
    def __init__(self):
        self.supported_formats = ['.xls', '.xlsx']
    
    def _get_file_extension(self, filepath: str) -> str:
        """Get the file extension from filepath"""
        return Path(filepath).suffix.lower()
    
    def _validate_file(self, filepath: str) -> bool:
        """Validate if file exists and has supported format"""
        file_path = Path(filepath)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        if self._get_file_extension(filepath) not in self.supported_formats:
            raise ValueError(f"Unsupported file format. Supported formats: {self.supported_formats}")
        
        return True
    
    def _get_engine_for_file(self, filepath: str) -> Literal['xlrd', 'openpyxl']:
        """Determine the appropriate pandas engine based on file extension"""
        extension = self._get_file_extension(filepath)
        if extension == '.xls':
            return 'xlrd'
        elif extension == '.xlsx':
            return 'openpyxl'
        else:
            raise ValueError(f"No engine available for file type: {extension}")
    
    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean the dataframe with column renaming and filtering"""
        # Rename columns to match the Item model
        column_mapping = {
            "Unnamed: 0": "operation_date", # Fecha Operación   
            "Unnamed: 1": "value_date", # Fecha Valor
            "Cuenta Smart": "concept", # Concepto
            "FECHA": "amount", # Importe
            "Unnamed: 4": "salary" # Saldo
        }
        
        df = df.rename(columns=column_mapping)
        
        # Find first row where 'salary' is a float and filter from there
        if "salary" in df.columns:
            df = df.dropna(subset=["salary"])  # Remove rows where salary is NaN
        
        return df
    
    def read_file_to_records(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Read Excel file and return list of dictionaries ready for Item model
        
        Args:
            filepath: Path to the Excel file (.xls or .xlsx)
            
        Returns:
            List of dictionaries with expense data
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
            Exception: For other file reading errors
        """
        try:
            self._validate_file(filepath)
            engine = self._get_engine_for_file(filepath)
            
            data_rows = []
            
            with Path(filepath).open(mode="rb") as file:
                excel_data = pd.read_excel(file, sheet_name=None, engine=engine)
                
                for sheet_name, df in excel_data.items():
                    processed_df = self._process_dataframe(df)
                    records = processed_df.to_dict(orient="records")
                    data_rows.extend(records)
            
            return data_rows
            
        except FileNotFoundError:
            print(f"File not found: {filepath}")
            return []
        except Exception as e:
            print(f"Error reading file {filepath}: {e}")
            return []
    
    def convert_european_number_to_float(self, value):
        """Convert European number format to float for charts"""
        if pd.isna(value) or value == '' or value is None:
            return 0.0
        if isinstance(value, str):
            # Remove dots (thousands separator) and replace comma with dot (decimal separator)
            cleaned = value.replace('.', '').replace(',', '.')
            try:
                return float(cleaned)
            except ValueError:
                return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        return 0.0
    