#modules/utilities.py
import json
from typing import Dict
import pandas as pd

def load_categories(path: str) -> Dict[str, list]:
    """
    Carga las categorías desde un archivo JSON.

    :param path: Ruta al archivo JSON de categorías.
    :return: Diccionario de categorías.
    """
    try:
        with open(path, "r", encoding='utf-8') as file:
            categories = json.load(file)
        return categories
    except FileNotFoundError:
        raise FileNotFoundError(f"No se encontró el archivo de categorías en: {path}")
    except json.JSONDecodeError:
        raise ValueError(f"El archivo de categorías en {path} no es un JSON válido.")
    
def load_expenses(csv_path: str):
    try:
        df = pd.read_csv(csv_path)
        print(f"Datos cargados exitosamente desde {csv_path}.")
        return df
    except FileNotFoundError:
        print(f"No se encontró el archivo CSV en: {csv_path}")
    except pd.errors.ParserError:
        print(f"El archivo CSV en {csv_path} no se pudo analizar correctamente.")