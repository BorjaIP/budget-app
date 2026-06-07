import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal

import pandas as pd


_DATE_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s*$")


def to_iso_date(value: Any) -> str | None:
    """Convert a dd/mm/yyyy string or pandas Timestamp to ISO yyyy-mm-dd."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        match = _DATE_RE.match(value)
        if match:
            day, month, year = match.groups()
            return f"{year}-{int(month):02d}-{int(day):02d}"
    return None


def european_to_float(value: Any) -> float | None:
    """Parse a number to float, accepting European ('1.234,56'), US ('1234.56') or plain."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        has_comma = "," in s
        has_dot = "." in s
        if has_comma and has_dot:
            s = s.replace(".", "").replace(",", ".")
        elif has_comma:
            s = s.replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def compute_dedupe_hash(
    operation_date: str, amount: float, concept: str, bank_name: str | None
) -> str:
    payload = f"{operation_date}|{amount:.2f}|{concept[:80].strip().lower()}|{bank_name or ''}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def infer_bank_from_filename(filename: str) -> str | None:
    stem = Path(filename).stem.lower()
    known = {
        "bbva": "BBVA",
        "santander": "Santander",
        "caixa": "CaixaBank",
        "caixabank": "CaixaBank",
        "ing": "ING",
        "openbank": "Openbank",
        "sabadell": "Sabadell",
        "bankinter": "Bankinter",
        "kutxabank": "Kutxabank",
        "n26": "N26",
        "revolut": "Revolut",
        "wise": "Wise",
    }
    for token, label in known.items():
        if token in stem:
            return label
    return None


class FileReader:
    """Reads .xls/.xlsx bank exports and returns normalized expense records."""

    SUPPORTED_FORMATS = (".xls", ".xlsx")

    _COLUMN_ALIASES: Dict[str, set] = {
        "operation_date": {"Unnamed: 0", "FECHA OPERACIÓN", "FECHA OPERACION", "Fecha Operación"},
        "value_date": {"Unnamed: 1", "FECHA VALOR", "Fecha Valor"},
        "concept": {"Cuenta Smart", "CONCEPTO", "Concepto"},
        "amount": {"FECHA", "IMPORTE EUR", "IMPORTE", "Importe"},
        "balance": {"Unnamed: 4", "SALDO", "Saldo"},
    }
    _TARGET_COLUMNS = ["operation_date", "value_date", "concept", "amount", "balance"]

    def _validate_file(self, filepath: str) -> None:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format. Supported: {self.SUPPORTED_FORMATS}"
            )

    def _engine_for(self, filepath: str) -> Literal["xlrd", "openpyxl"]:
        return "xlrd" if Path(filepath).suffix.lower() == ".xls" else "openpyxl"

    def _build_column_mapping(self, columns: List[str]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}
        for target, aliases in self._COLUMN_ALIASES.items():
            for col in columns:
                if col in aliases:
                    mapping[col] = target
                    break
        unmapped_targets = [t for t in self._TARGET_COLUMNS if t not in mapping.values()]
        unmapped_sources = [c for c in columns if c not in mapping]
        if len(unmapped_targets) == 1 and len(unmapped_sources) == 1:
            mapping[unmapped_sources[0]] = unmapped_targets[0]
        return mapping

    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.rename(columns=self._build_column_mapping(list(df.columns)))
        if "balance" in df.columns:
            df = df.dropna(subset=["balance"])
            df = df[df["balance"].apply(lambda v: european_to_float(v) is not None)]
        return df

    def read_file_to_records(
        self, filepath: str, bank_name: str | None = None
    ) -> List[Dict[str, Any]]:
        """Read Excel and return normalized records ready for ExpenseCreate.

        Each record has: operation_date (ISO), value_date (ISO), concept,
        amount (float), balance (float), bank_name, dedupe_hash.
        """
        self._validate_file(filepath)
        bank = bank_name or infer_bank_from_filename(filepath)

        records: List[Dict[str, Any]] = []
        with Path(filepath).open(mode="rb") as fh:
            sheets = pd.read_excel(fh, sheet_name=None, engine=self._engine_for(filepath))

        for _, df in sheets.items():
            df = self._process_dataframe(df)
            for raw in df.to_dict(orient="records"):
                normalized = self._normalize_row(raw, bank)
                if normalized is not None:
                    records.append(normalized)
        return records

    def _normalize_row(self, raw: Dict[str, Any], bank: str | None) -> Dict[str, Any] | None:
        operation_date = to_iso_date(raw.get("operation_date"))
        value_date = to_iso_date(raw.get("value_date")) or operation_date
        concept = str(raw.get("concept") or "").strip()
        amount = european_to_float(raw.get("amount"))
        balance = european_to_float(raw.get("balance"))

        if not operation_date or amount is None or balance is None or not concept:
            return None

        return {
            "operation_date": operation_date,
            "value_date": value_date,
            "concept": concept,
            "amount": amount,
            "balance": balance,
            "bank_name": bank,
            "dedupe_hash": compute_dedupe_hash(operation_date, amount, concept, bank),
        }
