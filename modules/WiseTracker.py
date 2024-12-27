# modules/WiseTracker.py

import json
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Optional
import os

from modules.utilities import load_categories, load_expenses

class WiseTracker:
    def __init__(self, categories_path: str, exchange_rates: Dict[str, float], base_currency: str = 'EUR', csv_path: str = 'transaction-history.csv'):
        self.base_currency = base_currency
        self.exchange_rates = exchange_rates
        self.categories_path = categories_path
        self.categories = self._load_categories(categories_path)
        self.df = load_expenses(csv_path=csv_path)
        self.process_data()
        print(self.df.head())

    def _load_categories(self, path: str) -> Dict[str, list]:
        try:
            with open(path, "r", encoding='utf-8') as file:
                categories = json.load(file)
            return categories
        except FileNotFoundError:
            print(f"No se encontró el archivo de categorías en: {path}")
            return {}
        except json.JSONDecodeError:
            print(f"El archivo de categorías en {path} no es un JSON válido.")
            return {}

    def save_categories(self):
        try:
            with open(self.categories_path, "w", encoding='utf-8') as file:
                json.dump(self.categories, file, ensure_ascii=False, indent=4)
            print("Categorías guardadas exitosamente.")
        except Exception as e:
            print(f"Error al guardar las categorías: {e}")

    def convert_to_base_currency(self, amount: float, source_currency: str) -> float:
        if source_currency not in self.exchange_rates:
            raise ValueError(f"Tasa de cambio no definida para la divisa: {source_currency}")
        rate = self.exchange_rates[source_currency]
        return amount * rate

    def categorize_expense(self, target_name: str) -> str:
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.lower() in target_name.lower():
                    return category
        return "Otros"

    def add_category_column(self):
        if 'Target name' not in self.df.columns:
            print("El DataFrame no contiene la columna 'Target name'.")
            return
        
        self.df['Target name'] = self.df['Target name'].astype(str).fillna('')
        self.df['Categoría'] = self.df['Target name'].apply(self.categorize_expense)
        print("Columna 'Categoría' agregada exitosamente.")

    def add_month_column(self):
        if 'Created on' not in self.df.columns:
            print("El DataFrame no contiene la columna 'Created on'.")
            return
        
        self.df["Created on"] = pd.to_datetime(self.df["Created on"], errors='coerce')
        if self.df["Created on"].isnull().any():
            print("Algunas fechas en 'Created on' no pudieron convertirse a datetime.")
        
        self.df["Año_Mes"] = self.df["Created on"].dt.to_period('M')
        print("Columna 'Año_Mes' agregada exitosamente.")

    def convert_amounts_to_base_currency(self, 
                                         amount_column: str = 'Target amount (after fees)', 
                                         currency_column: str = 'Target currency', 
                                         new_amount_column: str = 'Amount in EUR'):
        required_columns = {amount_column, currency_column}
        if not required_columns.issubset(self.df.columns):
            missing = required_columns - set(self.df.columns)
            print(f"El DataFrame está perdiendo las siguientes columnas necesarias: {missing}")
            return
        
        self.df[amount_column] = pd.to_numeric(self.df[amount_column], errors='coerce').fillna(0.0)
        self.df[currency_column] = self.df[currency_column].astype(str).fillna(self.base_currency)
        
        self.df[new_amount_column] = self.df.apply(
            lambda row: self.convert_to_base_currency(row[amount_column], row[currency_column]), axis=1
        )
        print(f"Columna '{new_amount_column}' agregada exitosamente.")

    def process_data(self):
        # Recalcular las columnas necesarias cada vez que se procesa
        self.add_category_column()
        self.add_month_column()
        self.convert_amounts_to_base_currency()
        self.add_category_column()
        print("Procesamiento de datos completado.")

    def net_amount_per_month(self) -> pd.Series:
        required_columns = {'Año_Mes', 'Amount in EUR', 'Direction'}
        if not required_columns.issubset(self.df.columns):
            missing = required_columns - set(self.df.columns)
            raise ValueError(f"El DataFrame está perdiendo las siguientes columnas necesarias: {missing}")
        
        ingresos = self.df[self.df['Direction'].str.upper() == 'IN'].groupby('Año_Mes')['Amount in EUR'].sum()
        gastos = self.df[self.df['Direction'].str.upper() == 'OUT'].groupby('Año_Mes')['Amount in EUR'].sum()
        
        neto = ingresos.subtract(gastos, fill_value=0)
        neto.index = neto.index.astype(str)
        return neto

    def expenses_per_category_per_month(self, amount_column: str = 'Amount in EUR') -> pd.DataFrame:
        required_columns = {'Año_Mes', 'Categoría', amount_column, 'Direction'}
        if not required_columns.issubset(self.df.columns):
            missing = required_columns - set(self.df.columns)
            raise ValueError(f"El DataFrame está perdiendo las siguientes columnas necesarias: {missing}")
        
        gastos = self.df[self.df['Direction'].str.upper() == 'OUT'].copy()
        gastos_agrupados = gastos.groupby(['Año_Mes', 'Categoría'])[amount_column].sum().reset_index()
        gastos_pivot = gastos_agrupados.pivot(index='Año_Mes', columns='Categoría', values=amount_column).fillna(0)
        gastos_pivot = gastos_pivot.sort_index()
        return gastos_pivot
    
    def save_monthly_data(self, output_dir: str = 'monthly_data'):
        """
        Guarda archivos CSV separados para cada mes con transacciones clasificadas.
        No sobrescribe archivos CSV que ya existen.

        :param output_dir: Directorio donde se guardarán los CSV mensuales.
        """
        # Asegurar que el directorio de salida exista
        os.makedirs(output_dir, exist_ok=True)
        
        # Verificar si existe la columna 'Año_Mes'
        if 'Año_Mes' not in self.df.columns:
            print("La columna 'Año_Mes' no existe en el DataFrame.")
            return
        
        # Agrupar por 'Año_Mes'
        grouped = self.df.groupby('Año_Mes')
        
        for period, group in grouped:
            # Convertir Period a string para el nombre de archivo
            period_str = str(period)
            filename = f"{period_str}.csv"
            filepath = os.path.join(output_dir, filename)
            
            # Verificar si el archivo ya existe
            if os.path.exists(filepath):
                print(f"El archivo '{filename}' ya existe. No se sobrescribe.")
                continue  # Salta a la siguiente iteración
            
            # Guardar el grupo en CSV
            group.to_csv(filepath, index=False)
            print(f"Datos guardados para {period_str} en {filepath}.")

    def plot_expenses(self, gastos_pivot: pd.DataFrame, currency: Optional[str] = None) -> Optional[plt.Figure]:
        if gastos_pivot.empty:
            print("No hay datos para graficar.")
            return None
        
        if currency is None:
            currency = self.base_currency
        
        fig, ax = plt.subplots(figsize=(12, 8))
        gastos_pivot.plot(kind='bar', stacked=True, ax=ax)
        ax.set_title(f'Gastos por Categoría y Mes ({currency})')
        ax.set_xlabel('Mes')
        ax.set_ylabel(f'Monto Gastado ({currency})')
        ax.legend(title='Categoría', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        return fig