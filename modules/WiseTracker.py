# modules/WiseTracker.py

import json
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Optional
import os

from modules.utilities import load_categories, load_expenses

class WiseTracker:
    def __init__(self, categories_path: str, base_currency: str = 'EUR', csv_path: str = 'wise.csv'):
        self.base_currency = base_currency
        self.categories_path = categories_path
        self.categories = self._load_categories(categories_path)
        self.df = load_expenses(csv_path=csv_path)
        self.process_data()
        print(self.df.head())

    def data_check(self):
        # Deal withEmpty values in 'Target name', 'Reference', 'Source amount (after fees)', 'Source fee amount', 'Created on', 'Direction', 'ID'
        self.df['Target name'] = self.df['Target name'].fillna('')
        self.df['Reference'] = self.df['Reference'].fillna('')
        self.df['Source amount (after fees)'] = self.df['Source amount (after fees)'].fillna(0)
        self.df['Source fee amount'] = self.df['Source fee amount'].fillna(0)
        self.df['Created on'] = self.df['Created on'].fillna('')
        self.df['Direction'] = self.df['Direction'].fillna('')
        self.df['ID'] = self.df['ID'].fillna('')
        print("Empty values have been filled.")


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
        
        # If row has column the string 'TRANSFER' in column 'ID', then it is classified based on 'Reference'. If not, it is classified based on 'Target name'.
        self.df['Categoría'] = self.df.apply(
            lambda row: self.categorize_expense(row['Target name']) if 'TRANSFER' not in row['ID'] else self.categorize_expense(row['Reference']), axis=1)
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

    def total_amount(self,after_fees: str = 'Source amount (after fees)', fees: str = 'Source fee amount', new_amount_column = 'Amount in EUR') -> pd.Series:

        #################### MANERA INCORRECTA DE MANEJAR DISTINTAS DIVISAS ####################
        # required_columns = {after_fees, fees}
        # if not required_columns.issubset(self.df.columns):
        #     missing = required_columns - set(self.df.columns)
        #     print(f"El DataFrame está perdiendo las siguientes columnas necesarias: {missing}")
        #     return
        
        # self.df[after_fees] = pd.to_numeric(self.df[after_fees], errors='coerce').fillna(0.0)
        # self.df[fees] = pd.to_numeric(self.df[after_fees], errors='coerce').fillna(0.0)
        
        # self.df[new_amount_column] = self.df.apply(
        #     lambda row: row[after_fees] + row[fees], axis=1)
        
        # print(f"Columna '{new_amount_column}' agregada exitosamente.")

        #################### AÑADIR COMO 'Amount in EUR' la columna 'Source amount (after fees)' ####################
        # Fill na values with 0
        self.df[new_amount_column] = self.df[after_fees].fillna(0)

    def process_data(self):
        self.data_check()
        # Recalcular las columnas necesarias cada vez que se procesa
        self.add_month_column()
        self.total_amount()
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
        
        # Tomo los gastos y los ingresos
        gastos = self.df[self.df['Direction'].str.upper() == 'OUT'].copy()
        ingresos = self.df[self.df['Direction'].str.upper() == 'IN'].copy()

        # Agrupo por 'Año_Mes' y 'Categoría' y calculo cuanto he gastado en cada categoría por mes teniendo en cuenta los ingresos y los gastos
        gastos_pivot = gastos.groupby(['Año_Mes', 'Categoría'])[amount_column].sum().unstack().fillna(0)
        ingresos_pivot = ingresos.groupby(['Año_Mes', 'Categoría'])[amount_column].sum().unstack().fillna(0)
        neto_pivot = ingresos_pivot.subtract(gastos_pivot, fill_value=0)
        neto_pivot.index = neto_pivot.index.astype(str)

        # neto must be in positive values. Since normally we have more expenses than incomes, we will set to 0 the negative values and will set positive values to zero.
        neto_pivot = neto_pivot.applymap(lambda x: -x if x < 0 else 0)
        return gastos_pivot, ingresos_pivot, neto_pivot
    
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