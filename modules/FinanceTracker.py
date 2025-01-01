# modules/FinanceTracker.py

import json
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Optional, Tuple
import os

from modules.utilities import load_categories, load_expenses  # Ensure these utility functions are compatible or adjust accordingly


class FinanceTracker:
    def __init__(
        self,
        categories_path: str,
        base_currency: str = 'EUR',
        wise_csv_path: str = 'wise.csv',
        revolut_csv_path: str = 'revolut.csv'
    ):
        """
        Initializes the FinanceTracker by loading and combining Wise and Revolut transaction data.

        :param categories_path: Path to the JSON file containing category classifications.
        :param base_currency: The base currency for reporting (default is 'EUR').
        :param wise_csv_path: Path to the Wise transactions CSV file.
        :param revolut_csv_path: Path to the Revolut transactions CSV file.
        """
        self.base_currency = base_currency
        self.categories_path = categories_path
        self.categories = self._load_categories(categories_path)
        self.wise_csv_path = wise_csv_path
        self.revolut_csv_path = revolut_csv_path
        self.df = self._load_and_combine_data()
        self.process_data()
        print("Initial data loaded and processed successfully.")
        print(self.df.head())

    def _load_categories(self, path: str) -> Dict[str, list]:
        """
        Loads category classifications from a JSON file.

        :param path: Path to the JSON file.
        :return: Dictionary of categories and their associated keywords.
        """
        try:
            with open(path, "r", encoding='utf-8') as file:
                categories = json.load(file)
            print("Categories loaded successfully.")
            return categories
        except FileNotFoundError:
            print(f"Categories file not found at: {path}")
            return {}
        except json.JSONDecodeError:
            print(f"The categories file at {path} is not a valid JSON.")
            return {}

    def save_categories(self):
        """
        Saves the current category classifications back to the JSON file.
        """
        try:
            with open(self.categories_path, "w", encoding='utf-8') as file:
                json.dump(self.categories, file, ensure_ascii=False, indent=4)
            print("Categories saved successfully.")
        except Exception as e:
            print(f"Error saving categories: {e}")

    def _load_wise_data(self) -> pd.DataFrame:
        """
        Loads and standardizes Wise transaction data.

        :return: Standardized Wise transactions DataFrame.
        """
        try:
            df_wise = load_expenses(csv_path=self.wise_csv_path)
            if df_wise.empty:
                print("Wise CSV is empty or not loaded correctly.")
                return pd.DataFrame()
            # Rename columns to standardize
            df_wise.rename(columns={
                'ID': 'Transaction ID',
                'Status': 'Status',
                'Direction': 'Type',
                'Created on': 'Started Date',
                'Finished on': 'Completed Date',
                'Source fee amount': 'Fee',
                'Source fee currency': 'Fee Currency',
                'Target fee amount': 'Target Fee',
                'Target fee currency': 'Target Fee Currency',
                'Source name': 'Source',
                'Source amount (after fees)': 'Amount',
                'Source currency': 'Currency',
                'Target name': 'Description',
                'Target amount (after fees)': 'Target Amount',
                'Target currency': 'Target Currency',
                'Exchange rate': 'Exchange Rate',
                'Reference': 'Reference',
                'Batch': 'Batch',
                'Created by': 'Created By'
            }, inplace=True)
            df_wise['Source Platform'] = 'Wise'
            print("Wise data loaded and standardized.")
            return df_wise
        except Exception as e:
            print(f"Error loading Wise data: {e}")
            return pd.DataFrame()

    def _load_revolut_data(self) -> pd.DataFrame:
        """
        Loads and standardizes Revolut transaction data.

        :return: Standardized Revolut transactions DataFrame.
        """
        try:
            df_revolut = load_expenses(csv_path=self.revolut_csv_path)
            if df_revolut.empty:
                print("Revolut CSV is empty or not loaded correctly.")
                return pd.DataFrame()
            # Rename columns to standardize
            df_revolut.rename(columns={
                'Type': 'Type',
                'Product': 'Product',
                'Started Date': 'Started Date',
                'Completed Date': 'Completed Date',
                'Description': 'Description',
                'Amount': 'Amount',
                'Fee': 'Fee',
                'Currency': 'Currency',
                'State': 'State',
                'Balance': 'Balance'
            }, inplace=True)
            df_revolut['Source Platform'] = 'Revolut'
            print("Revolut data loaded and standardized.")
            return df_revolut
        except Exception as e:
            print(f"Error loading Revolut data: {e}")
            return pd.DataFrame()

    def _load_and_combine_data(self) -> pd.DataFrame:
        """
        Loads both Wise and Revolut data and combines them into a single DataFrame.

        :return: Combined DataFrame of Wise and Revolut transactions.
        """
        df_wise = self._load_wise_data()
        df_revolut = self._load_revolut_data()

        # Define a list of unified columns
        unified_columns = [
            'Transaction ID', 'Status', 'Type', 'Started Date', 'Completed Date',
            'Description', 'Amount', 'Fee', 'Currency', 'State', 'Balance',
            'Target Amount', 'Target Currency', 'Exchange Rate',
            'Reference', 'Batch', 'Created By', 'Product', 'Target Fee',
            'Target Fee Currency', 'Source Platform'
        ]

        # Add missing columns to Revolut DataFrame
        for col in unified_columns:
            if col not in df_revolut.columns:
                df_revolut[col] = None

        # Add missing columns to Wise DataFrame
        for col in unified_columns:
            if col not in df_wise.columns:
                df_wise[col] = None

        # Combine DataFrames
        combined_df = pd.concat([df_wise, df_revolut], ignore_index=True, sort=False)

        # Select unified columns
        combined_df = combined_df[unified_columns]

        print("Wise and Revolut data combined successfully.")
        return combined_df

    def data_check(self):
        """
        Ensures all required columns are present and fills missing values appropriately.
        """
        required_columns = [
            'Transaction ID', 'Status', 'Type', 'Started Date', 'Completed Date',
            'Description', 'Amount', 'Fee', 'Currency', 'State', 'Balance',
            'Target Amount', 'Target Currency', 'Exchange Rate',
            'Reference', 'Batch', 'Created By', 'Product', 'Target Fee',
            'Target Fee Currency', 'Source Platform'
        ]
        for col in required_columns:
            if col not in self.df.columns:
                self.df[col] = ''

        # Fill missing values appropriately
        self.df['Transaction ID'] = self.df['Transaction ID'].fillna('')
        self.df['Status'] = self.df['Status'].fillna('')
        self.df['Type'] = self.df['Type'].fillna('')
        self.df['Started Date'] = self.df['Started Date'].fillna('')
        self.df['Completed Date'] = self.df['Completed Date'].fillna('')
        self.df['Description'] = self.df['Description'].fillna('')
        self.df['Amount'] = pd.to_numeric(self.df['Amount'], errors='coerce').fillna(0.0)
        self.df['Fee'] = pd.to_numeric(self.df['Fee'], errors='coerce').fillna(0.0)
        self.df['Currency'] = self.df['Currency'].fillna(self.base_currency)
        self.df['State'] = self.df['State'].fillna('')
        self.df['Balance'] = pd.to_numeric(self.df['Balance'], errors='coerce').fillna(0.0)
        self.df['Target Amount'] = pd.to_numeric(self.df['Target Amount'], errors='coerce').fillna(0.0)
        self.df['Target Currency'] = self.df['Target Currency'].fillna(self.base_currency)
        self.df['Exchange Rate'] = self.df['Exchange Rate'].fillna(1.0)
        self.df['Reference'] = self.df['Reference'].fillna('')
        self.df['Batch'] = self.df['Batch'].fillna('')
        self.df['Created By'] = self.df['Created By'].fillna('')
        self.df['Product'] = self.df['Product'].fillna('')
        self.df['Target Fee'] = pd.to_numeric(self.df['Target Fee'], errors='coerce').fillna(0.0)
        self.df['Target Fee Currency'] = self.df['Target Fee Currency'].fillna(self.base_currency)
        self.df['Source Platform'] = self.df['Source Platform'].fillna('Unknown')
        print("Empty values have been filled.")

    def categorize_expense(self, description: str) -> str:
        """
        Categorizes a transaction based on its description.

        :param description: Description of the transaction.
        :return: Category name.
        """
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in description.lower():
                    return category
        return "Others"

    def add_category_column(self):
        """
        Adds a 'Category' column to the DataFrame by categorizing each transaction.
        """
        if 'Description' not in self.df.columns:
            print("The DataFrame does not contain the 'Description' column.")
            return

        # Apply categorization based on 'Description'
        self.df['Category'] = self.df['Description'].apply(self.categorize_expense)
        print("Category column added successfully.")

    def add_month_column(self):
        """
        Adds 'Year_Month' and converts 'Started Date' and 'Completed Date' to datetime.
        """
        # Convert 'Started Date' to datetime
        if 'Started Date' not in self.df.columns:
            print("The DataFrame does not contain the 'Started Date' column.")
            return

        self.df["Started Date"] = pd.to_datetime(self.df["Started Date"], errors='coerce')
        if self.df["Started Date"].isnull().any():
            print("Some dates in 'Started Date' could not be converted to datetime.")

        # Convert 'Completed Date' to datetime
        if 'Completed Date' not in self.df.columns:
            print("The DataFrame does not contain the 'Completed Date' column.")
            return

        self.df["Completed Date"] = pd.to_datetime(self.df["Completed Date"], errors='coerce')
        if self.df["Completed Date"].isnull().any():
            print("Some dates in 'Completed Date' could not be converted to datetime.")

        # Create 'Year_Month' column based on 'Completed Date'
        self.df["Year_Month"] = self.df["Completed Date"].dt.to_period('M')
        print("Year_Month and date columns added successfully.")

    def total_amount(self, amount_col: str = 'Amount', fee_col: str = 'Fee', new_amount_column: str = 'Amount in EUR') -> pd.Series:
        """
        Adds a new column representing the total amount in EUR.
        For Wise transactions, it's 'Amount'.
        For Revolut transactions, it's 'Amount'.

        :param amount_col: Column name for the main amount.
        :param fee_col: Column name for the fee amount.
        :param new_amount_column: Name of the new column to be added.
        :return: The newly added column.
        """
        # For both Wise and Revolut, since exchange rates are removed, directly assign 'Amount'
        self.df[new_amount_column] = self.df[amount_col].fillna(0)
        print(f"Column '{new_amount_column}' added successfully.")

    def process_data(self):
        """
        Processes the data by performing data checks, categorization, and adding necessary columns.
        """
        self.data_check()
        self.add_month_column()
        self.total_amount()
        self.add_category_column()
        print("Data processing completed.")

    def net_amount_per_month(self) -> pd.Series:
        """
        Calculates the net amount (incomes minus expenses) per month.

        :return: Series representing net amount per month.
        """
        required_columns = {'Year_Month', 'Amount in EUR', 'Type'}
        if not required_columns.issubset(self.df.columns):
            missing = required_columns - set(self.df.columns)
            raise ValueError(f"The DataFrame is missing the following required columns: {missing}")

        # Define transaction types for income and expenses
        income_types = ['IN', 'DEPOSIT', 'REFUND', 'INCOME']
        expense_types = ['OUT', 'WITHDRAWAL', 'PAYMENT', 'EXPENSE']

        incomes = self.df[self.df['Type'].str.upper().isin(income_types)].groupby('Year_Month')['Amount in EUR'].sum()
        expenses = self.df[self.df['Type'].str.upper().isin(expense_types)].groupby('Year_Month')['Amount in EUR'].sum()

        net = incomes.subtract(expenses, fill_value=0)
        net.index = net.index.astype(str)
        return net

    def expenses_per_category_per_month(self, amount_column: str = 'Amount in EUR') -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Calculates expenses, incomes, and net amounts per category and month.

        :param amount_column: Column name for the amount.
        :return: Tuple containing expenses pivot, incomes pivot, and net pivot DataFrames.
        """
        required_columns = {'Year_Month', 'Category', amount_column, 'Type'}
        if not required_columns.issubset(self.df.columns):
            missing = required_columns - set(self.df.columns)
            raise ValueError(f"The DataFrame is missing the following required columns: {missing}")

        # Define transaction types for income and expenses
        income_types = ['IN', 'DEPOSIT', 'REFUND', 'INCOME']
        expense_types = ['OUT', 'WITHDRAWAL', 'PAYMENT', 'EXPENSE']

        # Separate expenses and incomes
        expenses = self.df[self.df['Type'].str.upper().isin(expense_types)].copy()
        incomes = self.df[self.df['Type'].str.upper().isin(income_types)].copy()

        # Group by Year_Month and Category
        expenses_pivot = expenses.groupby(['Year_Month', 'Category'])[amount_column].sum().unstack().fillna(0)
        incomes_pivot = incomes.groupby(['Year_Month', 'Category'])[amount_column].sum().unstack().fillna(0)
        net_pivot = incomes_pivot.subtract(expenses_pivot, fill_value=0)
        net_pivot.index = net_pivot.index.astype(str)

        # Convert net_pivot to show expenses as positive and incomes as negative
        net_pivot = net_pivot.applymap(lambda x: -x if x < 0 else 0)
        print("Expenses, incomes, and net amounts per category and month calculated successfully.")
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
        """
        Generates a stacked bar chart for expenses by category and month.

        :param expenses_pivot: Pivot table of expenses by category and month.
        :param currency: Currency symbol or code for labeling (default is base_currency).
        :return: Matplotlib figure object.
        """
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
        print("Expenses plot generated successfully.")
        return fig

    def plot_net_expenses(self, net_pivot: pd.DataFrame, currency: Optional[str] = None) -> Optional[plt.Figure]:
        """
        Generates a stacked bar chart for net expenses by category and month.

        :param net_pivot: Pivot table of net expenses by category and month.
        :param currency: Currency symbol or code for labeling (default is base_currency).
        :return: Matplotlib figure object.
        """
        if net_pivot.empty:
            print("No net expense data available for plotting.")
            return None

        if currency is None:
            currency = self.base_currency

        fig, ax = plt.subplots(figsize=(12, 8))
        net_pivot.plot(kind='bar', stacked=True, ax=ax)
        ax.set_title(f'Net Expenses by Category and Month ({currency})')
        ax.set_xlabel('Month')
        ax.set_ylabel(f'Net Amount ({currency})')
        ax.legend(title='Category', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        print("Net expenses plot generated successfully.")
        return fig

    # Additional Methods (if needed)
    # def load_monthly_data(self, input_dir: str):
    #     """
    #     Loads monthly CSV files from the specified directory and integrates them into the main DataFrame.
    #     """
    #     # Implement loading logic if required
    #     pass