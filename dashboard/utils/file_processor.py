import shutil
from datetime import datetime
from pathlib import Path
from typing import List

from ..database.models import ExpenseCreate
from ..database.operations import db_manager
from .file_reader import FileReader


class FileProcessor:
    """Process uploaded Excel files: parse, dedupe-by-hash, insert."""

    def __init__(self, temp_folder: str = "data/temp_uploads"):
        self.temp_folder = Path(temp_folder)
        self.temp_folder.mkdir(parents=True, exist_ok=True)
        self.file_reader = FileReader()

    def save_uploaded_file(self, data: bytes, filename: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self.temp_folder / f"{timestamp}_{filename}"
        path.write_bytes(data)
        return str(path)

    def process_excel_file(self, file_path: str, bank_name: str | None = None) -> dict:
        try:
            filename = Path(file_path).name
            records = self.file_reader.read_file_to_records(file_path, bank_name=bank_name)
            if not records:
                return {
                    "status": "error",
                    "message": "No se encontraron movimientos válidos en el archivo.",
                    "inserted": 0,
                    "skipped": 0,
                }

            expenses = [
                ExpenseCreate(
                    operation_date=r["operation_date"],
                    value_date=r["value_date"],
                    concept=r["concept"],
                    amount=r["amount"],
                    balance=r["balance"],
                    bank_name=r["bank_name"],
                    dedupe_hash=r["dedupe_hash"],
                    file_source=filename,
                )
                for r in records
            ]
            result = db_manager.bulk_insert_with_dedupe(expenses, file_source=filename)
            return {
                "status": "success",
                "message": (
                    f"{result['inserted']} movimientos nuevos · "
                    f"{result['skipped']} duplicados ignorados"
                ),
                "inserted": result["inserted"],
                "skipped": result["skipped"],
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Error procesando archivo: {exc}",
                "inserted": 0,
                "skipped": 0,
            }

    def preview_excel_file(self, file_path: str, bank_name: str | None = None) -> dict:
        """Parse a bank export without storing anything: counts, range and totals."""
        try:
            records = self.file_reader.read_file_to_records(file_path, bank_name=bank_name)
        except Exception as exc:
            return {"status": "error", "message": f"No se pudo leer el archivo: {exc}"}
        if not records:
            return {"status": "error", "message": "No se encontraron movimientos válidos en el archivo."}

        hashes = list({r["dedupe_hash"] for r in records})
        duplicates = db_manager.count_existing_hashes(hashes)
        dates = sorted(r["operation_date"] for r in records)
        return {
            "status": "success",
            "total": len(records),
            "new": max(len(hashes) - duplicates, 0),
            "duplicates": duplicates,
            "date_from": dates[0],
            "date_to": dates[-1],
            "income": round(sum(r["amount"] for r in records if r["amount"] > 0), 2),
            "spending": round(-sum(r["amount"] for r in records if r["amount"] < 0), 2),
        }

    def get_uploaded_files(self) -> List[str]:
        return [f.name for f in self.temp_folder.iterdir() if f.is_file()]

    def cleanup_temp_folder(self) -> None:
        if self.temp_folder.exists():
            shutil.rmtree(self.temp_folder)
            self.temp_folder.mkdir(exist_ok=True)


file_processor = FileProcessor()
