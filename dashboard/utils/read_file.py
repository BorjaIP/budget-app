from pathlib import Path

import pandas as pd


def read_xls_to_array(filepath: str):
    data_rows = []

    with Path(filepath).open(mode="rb") as file:
        xls = pd.read_excel(file, sheet_name=None, engine="xlrd")

        for _, df in xls.items():
            # Rename columns
            df = df.rename(columns={"Unnamed: 0": "Fecha Operación"})
            df = df.rename(columns={"Unnamed: 1": "Fecha Valor"})
            df = df.rename(columns={"Cuenta Smart": "Concepto"})
            df = df.rename(columns={"FECHA": "Importe"})
            df = df.rename(columns={"Unnamed: 4": "Saldo"})

            # Find first row where 'Saldo' is a float
            if "Saldo" in df.columns:
                for i, value in enumerate(df["Saldo"]):
                    if isinstance(value, (int, float)) and not pd.isna(value):
                        df = df.iloc[i:]  # Keep rows from first valid float onward
                        break

            records = df.to_dict(orient="records")  # Each row as dict
            data_rows.extend(records)
            for row in records:
                print(row)  # Print each row (optional)

        return data_rows

    # except FileNotFoundError:
    #     print(f"File not found: {filepath}")
    #     return []
    # except Exception as e:
    #     print(f"Error reading file: {e}")
    #     return []


def read_xlsx_to_array(filepath: str):
    data_rows = []

    with Path(filepath).open(mode="rb") as file:
        xlsx = pd.read_excel(file, sheet_name=None, engine="openpyxl")

        for _, df in xlsx.items():
            # Rename columns
            df = df.rename(columns={"Unnamed: 0": "Fecha Operación"})
            df = df.rename(columns={"Unnamed: 1": "Fecha Valor"})
            df = df.rename(columns={"Cuenta Smart": "Concepto"})
            df = df.rename(columns={"FECHA": "Importe"})
            df = df.rename(columns={"Unnamed: 4": "Saldo"})

            # Find first row where 'Saldo' is a float
            if "Saldo" in df.columns:
                for i, value in enumerate(df["Saldo"]):
                    if isinstance(value, (int, float)) and not pd.isna(value):
                        df = df.iloc[i:]  # Keep rows from first valid float onward
                        break

            records = df.to_dict(orient="records")  # Each row as dict
            data_rows.extend(records)
            for row in records:
                print(row)  # Print each row (optional)

        return data_rows

    # except FileNotFoundError:
    #     print(f"File not found: {filepath}")
    #     return []
    # except Exception as e:
    #     print(f"Error reading file: {e}")
    #     return []


# Example usage
if __name__ == "__main__":
    # For .xls files
    try:
        xls_file_path = "../enero.xls"  # Replace with your .xls file path
        print("Reading XLS file:")
        read_xls_to_array(xls_file_path)
    except Exception as e:
        print(f"Error reading XLS file: {e}")
    
    # For .xlsx files
    try:
        xlsx_file_path = "../enero.xlsx"  # Replace with your .xlsx file path
        print("\nReading XLSX file:")
        read_xlsx_to_array(xlsx_file_path)
    except Exception as e:
        print(f"Error reading XLSX file: {e}")
