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
    
    # Known aliases for each target column across different bank export formats
    _COLUMN_ALIASES: Dict[str, set] = {
        "operation_date": {"Unnamed: 0", "FECHA OPERACIÓN", "FECHA OPERACION", "Fecha Operación"},
        "value_date": {"Unnamed: 1", "FECHA VALOR", "Fecha Valor"},
        "concept": {"Cuenta Smart", "CONCEPTO", "Concepto"},
        "amount": {"FECHA", "IMPORTE EUR", "IMPORTE", "Importe"},
        "salary": {"Unnamed: 4", "SALDO", "Saldo"},
    }
    _TARGET_COLUMNS = ["operation_date", "value_date", "concept", "amount", "salary"]

    def _build_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        """Build a column name mapping using known aliases, with positional fallback."""
        mapping: Dict[str, str] = {}
        for target, aliases in self._COLUMN_ALIASES.items():
            for col in columns:
                if col in aliases:
                    mapping[col] = target
                    break

        # If exactly one target is unmapped and one source column is unmapped, pair them
        mapped_targets = set(mapping.values())
        mapped_sources = set(mapping.keys())
        unmapped_targets = [t for t in self._TARGET_COLUMNS if t not in mapped_targets]
        unmapped_sources = [c for c in columns if c not in mapped_sources]
        if len(unmapped_targets) == 1 and len(unmapped_sources) == 1:
            mapping[unmapped_sources[0]] = unmapped_targets[0]

        return mapping

    def _is_date_value(self, value: Any) -> bool:
        """Check if a value looks like a dd/mm/yyyy date."""
        if not isinstance(value, str):
            return False
        import re
        return bool(re.match(r"^\d{2}/\d{2}/\d{4}$", value.strip()))

    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and clean the dataframe with column renaming and filtering"""
        columns = list(df.columns)
        column_mapping = self._build_column_mapping(columns)
        df = df.rename(columns=column_mapping)

        # Drop rows where salary is NaN
        if "salary" in df.columns:
            df = df.dropna(subset=["salary"])

        # Filter out header-like rows (salary value is not numeric)
        if "salary" in df.columns:
            df = df[df["salary"].apply(
                lambda v: isinstance(v, (int, float)) or (
                    isinstance(v, str) and v.replace('.', '').replace(',', '').replace('-', '').strip().isdigit()
                )
            )]

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
    