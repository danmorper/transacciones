# modules/RevolutTracker.py

import json
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Optional, Tuple
import os

from modules.utilities import load_categories, load_expenses  # Ensure these utility functions are compatible or adjust accordingly


class RevolutTracker:
    def __init__(
        self,
        categories_path: str,
        exchange_rates: Dict[str, float],
        base_currency: str = 'EUR',
        csv_path: str = 'revolut.csv'
    ):
        self.base_currency = base_currency
        self.exchange_rates = exchange_rates
        self.categories_path = categories_path
        self.categories = self._load_categories(categories_path)
        self.df = load_expenses(csv_path=csv_path)
        self.process_data()
        print(self.df.head())

    def data_check(self):
        # Handle empty values in relevant columns
        required_columns = [
            'Type', 'Product', 'Started Date', 'Completed Date',
            'Description', 'Amount', 'Fee', 'Currency', 'State', 'Balance'
        ]
        for col in required_columns:
            if col not in self.df.columns:
                self.df[col] = ''
        
        self.df['Type'] = self.df['Type'].fillna('')
        self.df['Product'] = self.df['Product'].fillna('')
        self.df['Started Date'] = self.df['Started Date'].fillna('')
        self.df['Completed Date'] = self.df['Completed Date'].fillna('')
        self.df['Description'] = self.df['Description'].fillna('')
        self.df['Amount'] = pd.to_numeric(self.df['Amount'], errors='coerce').fillna(0.0)
        self.df['Fee'] = pd.to_numeric(self.df['Fee'], errors='coerce').fillna(0.0)
        self.df['Currency'] = self.df['Currency'].fillna(self.base_currency)
        self.df['State'] = self.df['State'].fillna('')
        self.df['Balance'] = pd.to_numeric(self.df['Balance'], errors='coerce').fillna(0.0)
        print("Empty values have been filled.")

    def _load_categories(self, path: str) -> Dict[str, list]:
        try:
            with open(path, "r", encoding='utf-8') as file:
                categories = json.load(file)
            return categories
        except FileNotFoundError:
            print(f"Categories file not found at: {path}")
            return {}
        except json.JSONDecodeError:
            print(f"The categories file at {path} is not a valid JSON.")
            return {}

    def save_categories(self):
        try:
            with open(self.categories_path, "w", encoding='utf-8') as file:
                json.dump(self.categories, file, ensure_ascii=False, indent=4)
            print("Categories saved successfully.")
        except Exception as e:
            print(f"Error saving categories: {e}")

    def categorize_expense(self, description: str) -> str:
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in description.lower():
                    return category
        return "Others"

    def add_category_column(self):
        if 'Description' not in self.df.columns:
            print("The DataFrame does not contain the 'Description' column.")
            return
        
        # Classify based on 'Description' for all transaction types
        self.df['Category'] = self.df['Description'].apply(self.categorize_expense)
        print("Category column added successfully.")

    def add_month_column(self):
        if 'Completed Date' not in self.df.columns:
            print("The DataFrame does not contain the 'Completed Date' column.")
            return
        
        self.df["Completed Date"] = pd.to_datetime(self.df["Completed Date"], errors='coerce')
        if self.df["Completed Date"].isnull().any():
            print("Some dates in 'Completed Date' could not be converted to datetime.")
        
        self.df["Year_Month"] = self.df["Completed Date"].dt.to_period('M')
        print("Year_Month column added successfully.")

    def total_amount(self, amount_col: str = 'Amount', fee_col: str = 'Fee', new_amount_col: str = 'Amount in EUR') -> pd.Series:
        # Convert amounts to EUR using exchange rates
        self.df['Amount in EUR'] = self.df.apply(
            lambda row: (row[amount_col] + row[fee_col]) * self.exchange_rates.get(row['Currency'], 1.0),
            axis=1
        )
        print(f"Column '{new_amount_col}' added successfully.")

    def process_data(self):
        self.data_check()
        self.add_category_column()
        self.add_month_column()
        self.total_amount()
        print("Data processing completed.")

    def net_amount_per_month(self) -> pd.Series:
        required_columns = {'Year_Month', 'Amount in EUR', 'Type'}
        if not required_columns.issubset(self.df.columns):
            missing = required_columns - set(self.df.columns)
            raise ValueError(f"The DataFrame is missing the following required columns: {missing}")
        
        incomes = self.df[self.df['Type'].str.upper() == 'INCOME'].groupby('Year_Month')['Amount in EUR'].sum()
        expenses = self.df[self.df['Type'].str.upper() == 'EXPENSE'].groupby('Year_Month')['Amount in EUR'].sum()
        
        net = incomes.subtract(expenses, fill_value=0)
        net.index = net.index.astype(str)
        return net

    def expenses_per_category_per_month(self, amount_column: str = 'Amount in EUR') -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        required_columns = {'Year_Month', 'Category', amount_column, 'Type'}
        if not required_columns.issubset(self.df.columns):
            missing = required_columns - set(self.df.columns)
            raise ValueError(f"The DataFrame is missing the following required columns: {missing}")
        
        # Separate expenses and incomes
        expenses = self.df[self.df['Type'].str.upper() == 'EXPENSE'].copy()
        incomes = self.df[self.df['Type'].str.upper() == 'INCOME'].copy()

        # Group by Year_Month and Category
        expenses_pivot = expenses.groupby(['Year_Month', 'Category'])[amount_column].sum().unstack().fillna(0)
        incomes_pivot = incomes.groupby(['Year_Month', 'Category'])[amount_column].sum().unstack().fillna(0)
        net_pivot = incomes_pivot.subtract(expenses_pivot, fill_value=0)
        net_pivot.index = net_pivot.index.astype(str)

        # Convert net_pivot to show expenses as positive and incomes as negative
        net_pivot = net_pivot.applymap(lambda x: -x if x < 0 else 0)
        return expenses_pivot, incomes_pivot, net_pivot

    def save_monthly_data(self, output_dir: str = 'monthly_data'):
        """
        Saves separate CSV files for each month with classified transactions.
        Does not overwrite existing CSV files.

        :param output_dir: Directory where monthly CSVs will be saved.
        """
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Check if 'Year_Month' column exists
        if 'Year_Month' not in self.df.columns:
            print("The DataFrame does not contain the 'Year_Month' column.")
            return
        
        # Group by 'Year_Month'
        grouped = self.df.groupby('Year_Month')
        
        for period, group in grouped:
            # Convert Period to string for filename
            period_str = str(period)
            filename = f"{period_str}.csv"
            filepath = os.path.join(output_dir, filename)
            
            # Check if file already exists
            if os.path.exists(filepath):
                print(f"File '{filename}' already exists. Skipping.")
                continue  # Skip to the next iteration
            
            # Save the group to CSV
            group.to_csv(filepath, index=False)
            print(f"Data saved for {period_str} in {filepath}.")

    def plot_expenses(self, expenses_pivot: pd.DataFrame, currency: Optional[str] = None) -> Optional[plt.Figure]:
        if expenses_pivot.empty:
            print("No data available for plotting.")
            return None
        
        if currency is None:
            currency = self.base_currency
        
        fig, ax = plt.subplots(figsize=(12, 8))
        expenses_pivot.plot(kind='bar', stacked=True, ax=ax)
        ax.set_title(f'Expenses by Category and Month ({currency})')
        ax.set_xlabel('Month')
        ax.set_ylabel(f'Amount Spent ({currency})')
        ax.legend(title='Category', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        return fig