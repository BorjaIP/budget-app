from pathlib import Path
from typing import List

import pandas as pd
import reflex as rx

from dashboard.expenses.model import Item


class TableState(rx.State):

    items: List[Item] = []
    items_list: List[str] = []

    search_value: str = ""
    sort_value: str = ""
    sort_reverse: bool = False

    total_items: int = 0
    offset: int = 0
    limit: int = 12  # Number of rows per page

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

    def load_entries(self):
        with Path("enero.xls").open(mode="rb") as file:
            xls = pd.read_excel(file, sheet_name=None, engine="xlrd")

            for _, df in xls.items():
                # Rename columns
                df = df.rename(columns={"Unnamed: 0": "operation_date"})
                df = df.rename(columns={"Unnamed: 1": "value_date"})
                df = df.rename(columns={"Cuenta Smart": "concept"})
                df = df.rename(columns={"FECHA": "amount"})
                df = df.rename(columns={"Unnamed: 4": "salary"})

                # Find first row where 'salary' is a float
                if "salary" in df.columns:
                    for i, value in enumerate(df["salary"]):
                        if isinstance(value, (int, float)) and not pd.isna(value):
                            df = df.iloc[i:]  # Keep rows from first valid float onward
                            break

                reader = df.to_dict(orient="records")  # Each row as dict
                items = [Item(**row) for row in reader]  # type: ignore

                self.items = list(reversed(items))  # ordered list
                self.total_items = len(self.items)
                self.items_list = list(Item.__annotations__.keys())
            # self.extract_category()
            # print(self.items)

    def toggle_sort(self):
        self.sort_reverse = not self.sort_reverse
        self.load_entries()
