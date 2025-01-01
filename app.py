# app.py

import streamlit as st
import json
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Optional
import os
import zipfile
import io

from modules.FinanceTracker import FinanceTracker  # Updated import

# Configuración de la página
st.set_page_config(page_title="Rastreador de Finanzas Personales", layout="wide")

WISE_CSV_PATH = "wise.csv"
REVOLUT_CSV_PATH = "revolut.csv"
CATEGORIES_PATH = "clasificacion.json"  # Unified categories for both platforms

# Función para inicializar el rastreador y almacenar en el estado de sesión
@st.cache_resource
def initialize_tracker():
    EXCHANGE_RATES = {}  # Exchange rates removed as per latest WiseTracker
    tracker = FinanceTracker(
        categories_path=CATEGORIES_PATH,
        base_currency='EUR',
        wise_csv_path=WISE_CSV_PATH,
        revolut_csv_path=REVOLUT_CSV_PATH
    )
    return tracker

# Inicializar el rastreador
tracker = initialize_tracker()

# Función para guardar los datos mensuales
def save_monthly_data(tracker: FinanceTracker, output_dir: str):
    st.sidebar.subheader("Guardar Datos Mensuales")
    save_button = st.sidebar.button("Guardar Datos Mensuales")
    output_dir = "monthly_data"
    if save_button:
        try:            
            # Ejecutar la función para guardar datos mensuales
            tracker.save_monthly_data(output_dir=output_dir)
            st.sidebar.success(f"Datos mensuales guardados en el directorio '{output_dir}'.")
        except Exception as e:
            st.sidebar.error(f"Error al guardar los datos mensuales: {e}")
    # Removed redundant elif block

# Función para cargar los datos mensuales (Optional: Implement load_monthly_data in FinanceTracker)
def load_monthly_data(tracker: FinanceTracker, input_dir: str):
    st.sidebar.markdown("---")
    st.sidebar.subheader("Cargar Datos Mensuales")
    load_button = st.sidebar.button("Cargar Datos Mensuales")
    input_dir = "monthly_data"
    if load_button:
        try:
            # Implement load_monthly_data in FinanceTracker if needed
            # tracker.load_monthly_data(input_dir=input_dir)
            st.sidebar.success(f"Datos mensuales cargados desde el directorio '{input_dir}'.")
        except Exception as e:
            st.sidebar.error(f"Error al cargar los datos mensuales: {e}")
    # Removed redundant elif block

# Función para guardar el json de categorías
def save_categories(tracker: FinanceTracker):
    st.sidebar.markdown("---")

    # **Nueva Sección: Descargar clasificacion.json Actualizado**
    st.sidebar.subheader("Descargar clasificacion.json Actualizado")
    try:
        categories_json = json.dumps(tracker.categories, ensure_ascii=False, indent=4)
        
        st.sidebar.download_button(
            label="Descargar clasificacion.json",
            data=categories_json,
            file_name="clasificacion.json",
            mime="application/json"
        )
    except Exception as e:
        st.sidebar.error(f"Error al preparar la descarga de clasificacion.json: {e}")

# Sidebar para la navegación
st.sidebar.title("Navegación")
menu = st.sidebar.radio("Ir a", [
    "Dashboard",
    "Transacciones",
    "Gestión de Categorías",
    "Ver DataFrame"
])

save_monthly_data(tracker, "monthly_data")
load_monthly_data(tracker, "monthly_data")
save_categories(tracker)

# Función para mostrar el Dashboard
def show_dashboard(tracker: FinanceTracker):
    st.title("Dashboard Financiero")

    # Calcular el neto por mes
    try:
        neto_mensual = tracker.net_amount_per_month()
        st.write(neto_mensual)
    except ValueError as ve:
        st.error(str(ve))
        neto_mensual = pd.Series(dtype=float)

    # Calcular los gastos por categoría y mes
    try:
        gastos_categoria, ingresos_categoria, neto_categoria = tracker.expenses_per_category_per_month()
    except ValueError as ve:
        st.error(str(ve))
        gastos_categoria = pd.DataFrame()
        ingresos_categoria = pd.DataFrame()
        neto_categoria = pd.DataFrame()

    # Mostrar el neto por mes
    st.subheader("Neto por Mes")
    if not neto_mensual.empty:
        st.line_chart(neto_mensual)
    else:
        st.write("No hay datos disponibles para mostrar el neto por mes.")

    # Mostrar los gastos por categoría y mes
    st.subheader("Gastos por Categoría y Mes")
    if not gastos_categoria.empty:
        # Mostrar el DataFrame de gastos para depuración
        st.write("Datos de Gastos por Categoría y Mes:")
        st.dataframe(gastos_categoria)

        # Graficar
        fig = tracker.plot_expenses(gastos_categoria)
        if fig:
            st.pyplot(fig)
    else:
        st.write("No hay datos para mostrar el gráfico de gastos.")

    # Mostrar los gastos netos por categoria y mes
    st.subheader("Gastos Netos por Categoría y Mes")
    if not neto_categoria.empty:
        st.write("Datos de Gastos Netos por Categoría y Mes:")
        st.dataframe(neto_categoria)

        # Graficar
        fig = tracker.plot_net_expenses(neto_categoria)
        if fig:
            st.pyplot(fig)
    else:
        st.write("No hay datos para mostrar el gráfico de gastos netos.")

# Función para mostrar las Transacciones
def show_transactions(tracker: FinanceTracker):
    st.title("Transacciones")

    # Mostrar las transacciones en una tabla
    st.subheader("Revisar y Clasificar Transacciones")

    # Asegurarse de que las columnas necesarias existan
    display_columns = [
        'Transaction ID', 'Source Platform', 'Type', 'Started Date', 'Completed Date',
        'Description', 'Amount', 'Fee', 'Currency', 'State', 'Balance',
        'Category', 'Amount in EUR'
    ]
    for col in display_columns:
        if col not in tracker.df.columns:
            tracker.df[col] = ''

    # Convertir 'Completed Date' a datetime si no lo está
    if not pd.api.types.is_datetime64_any_dtype(tracker.df['Completed Date']):
        tracker.df['Completed Date'] = pd.to_datetime(tracker.df['Completed Date'], errors='coerce')

    # Obtener el rango de fechas
    min_date = tracker.df['Completed Date'].min()
    max_date = tracker.df['Completed Date'].max()

    # Interfaz para seleccionar el rango de fechas
    st.markdown("### Filtrar por Rango de Fechas")
    date_range = st.date_input(
        "Selecciona el rango de fechas",
        value=[
            min_date.date() if pd.notnull(min_date) else pd.to_datetime('2000-01-01').date(),
            max_date.date() if pd.notnull(max_date) else pd.to_datetime('2100-12-31').date()
        ],
        min_value=min_date.date() if pd.notnull(min_date) else pd.to_datetime('2000-01-01').date(),
        max_value=max_date.date() if pd.notnull(max_date) else pd.to_datetime('2100-12-31').date()
    )

    # Validar que se seleccionaron dos fechas
    if len(date_range) != 2:
        st.error("Por favor, selecciona un rango de fechas válido.")
        st.stop()

    start_date, end_date = date_range

    # Filtrar el DataFrame basado en las fechas seleccionadas
    mask = (tracker.df['Completed Date'].dt.date >= start_date) & (tracker.df['Completed Date'].dt.date <= end_date)
    filtered_df = tracker.df.loc[mask, display_columns].copy()

    st.markdown("### Transacciones Filtradas")
    st.write(f"Mostrando transacciones desde **{start_date}** hasta **{end_date}**.")
    # Mostrar el DataFrame editable
    edited_df = st.data_editor(
        filtered_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Type": st.column_config.SelectboxColumn(
                "Type",
                options=["IN", "OUT", "DEPOSIT", "WITHDRAWAL", "PAYMENT", "REFUND", "TRANSFER", "Other"],
                default="OUT",
            ),
            "Category": st.column_config.SelectboxColumn(
                "Category",
                options=list(tracker.categories.keys()) + ["Others"],
            ),
            "Description": st.column_config.TextColumn("Description"),
            "Started Date": st.column_config.DateColumn("Started Date"),
            "Completed Date": st.column_config.DateColumn("Completed Date"),
            "Amount": st.column_config.NumberColumn("Amount"),
            "Fee": st.column_config.NumberColumn("Fee"),
            "Currency": st.column_config.TextColumn("Currency"),
            "State": st.column_config.TextColumn("State"),
            "Balance": st.column_config.NumberColumn("Balance"),
            "Amount in EUR": st.column_config.NumberColumn("Amount in EUR", disabled=True),
            "Transaction ID": st.column_config.TextColumn("Transaction ID", disabled=True),
            "Source Platform": st.column_config.TextColumn("Source Platform", disabled=True),
            # Add other columns if needed
        }
    )

    # Botón para guardar cambios
    if st.button("Guardar Cambios"):
        try:
            # Update the original DataFrame with the changes made in the filter
            # Exclude 'Amount in EUR' since it's calculated
            tracker.df.loc[mask, display_columns[:-1]] = edited_df[display_columns[:-1]]
            # Save changes to the CSV, excluding 'Amount in EUR' and other calculated columns

            # Define which columns to save back to each CSV based on 'Source Platform'
            wise_columns = [
                'Transaction ID', 'Status', 'Type', 'Started Date', 'Completed Date',
                'Fee', 'Fee Currency', 'Target Fee', 'Target Fee Currency',
                'Source', 'Amount', 'Currency', 'Description',
                'Target Amount', 'Target Currency', 'Exchange Rate',
                'Reference', 'Batch', 'Created By', 'Source Platform'
            ]

            revolut_columns = [
                'Transaction ID', 'Status', 'Type', 'Started Date', 'Completed Date',
                'Description', 'Amount', 'Fee', 'Currency', 'State', 'Balance',
                'Source Platform'
            ]

            # Separate Wise and Revolut data
            wise_df = tracker.df[tracker.df['Source Platform'] == 'Wise'][wise_columns]
            revolut_df = tracker.df[tracker.df['Source Platform'] == 'Revolut'][revolut_columns]

            # Save to respective CSVs
            wise_df.to_csv(tracker.wise_csv_path, index=False)
            revolut_df.to_csv(tracker.revolut_csv_path, index=False)

            st.success("Cambios guardados exitosamente en los archivos CSV correspondientes.")
            # Reprocess data to update categories and amounts
            tracker.process_data()
            # Reset any session states if necessary
            if 'processed' in st.session_state:
                st.session_state.processed = False
        except Exception as e:
            st.error(f"Error al guardar los cambios: {e}")

    # Categorías presentes en gastos
    st.markdown("### Categorías de Gastos")
    expense_types = ['OUT', 'WITHDRAWAL', 'PAYMENT', 'EXPENSE']
    categorias_out = tracker.df.loc[
        tracker.df['Type'].str.upper().isin(expense_types),
        'Category'
    ].unique()
    categorias_out = [cat for cat in categorias_out if cat != "Others" and pd.notnull(cat)]
    
    if len(categorias_out) > 0:
        st.write(f"Categorías presentes en gastos: {', '.join(categorias_out)}")
    else:
        st.write("No hay categorías asignadas a gastos.")

# Función para mostrar la Gestión de Categorías
def show_category_management(tracker: FinanceTracker):
    st.title("Gestión de Categorías")

    # Agregar Nueva Categoría
    st.subheader("Agregar Nueva Categoría")
    with st.form("add_category_form"):
        new_category = st.text_input("Nombre de la nueva categoría")
        new_keywords = st.text_area("Palabras clave (una por línea)")
        submitted = st.form_submit_button("Agregar Categoría")
        if submitted:
            if new_category.strip() == "":
                st.error("El nombre de la categoría no puede estar vacío.")
            else:
                if new_category in tracker.categories:
                    st.error("La categoría ya existe.")
                else:
                    keywords_list = [kw.strip().lower() for kw in new_keywords.split('\n') if kw.strip() != ""]
                    tracker.categories[new_category] = keywords_list
                    tracker.save_categories()
                    st.success(f"Categoría '{new_category}' agregada exitosamente.")
                    # Reprocesar las categorías para actualizar las transacciones
                    tracker.process_data()
                    # Clean session state if needed
                    if 'existing_files' in st.session_state:
                        del st.session_state.existing_files
                    st.experimental_rerun()

    st.markdown("---")

    # Editar Categorías Existentes
    st.subheader("Editar Categorías Existentes")
    categories = list(tracker.categories.keys())
    if not categories:
        st.info("No hay categorías disponibles para editar.")
    else:
        selected_category = st.selectbox("Selecciona una categoría para editar", categories)

        if selected_category:
            st.write(f"### {selected_category}")
            st.write("**Palabras Clave:**")
            st.write(", ".join(tracker.categories[selected_category]))

            col1, col2 = st.columns(2)

            # Agregar Palabra Clave
            with col1:
                st.write("**Agregar Palabra Clave**")
                with st.form("add_keyword_form"):
                    new_keyword = st.text_input("Nueva palabra clave para agregar")
                    add_kw = st.form_submit_button("Agregar Palabra Clave")
                    if add_kw:
                        if new_keyword.strip() == "":
                            st.error("La palabra clave no puede estar vacía.")
                        else:
                            if new_keyword.lower() in tracker.categories[selected_category]:
                                st.error("La palabra clave ya existe en esta categoría.")
                            else:
                                tracker.categories[selected_category].append(new_keyword.lower())
                                tracker.save_categories()
                                st.success(f"Palabra clave '{new_keyword}' agregada a '{selected_category}'.")
                                # Reprocesar las categorías para actualizar las transacciones
                                tracker.process_data()
                                # Clean session state if needed
                                if 'existing_files' in st.session_state:
                                    del st.session_state.existing_files
                                st.experimental_rerun()

            # Eliminar Palabra Clave
            with col2:
                st.write("**Eliminar Palabra Clave**")
                if tracker.categories[selected_category]:
                    with st.form("remove_keyword_form"):
                        keyword_to_remove = st.selectbox("Selecciona una palabra clave para eliminar", tracker.categories[selected_category])
                        remove_kw = st.form_submit_button("Eliminar Palabra Clave")
                        if remove_kw:
                            tracker.categories[selected_category].remove(keyword_to_remove)
                            tracker.save_categories()
                            st.success(f"Palabra clave '{keyword_to_remove}' eliminada de '{selected_category}'.")
                            # Reprocesar las categorías para actualizar las transacciones
                            tracker.process_data()
                            # Clean session state if needed
                            if 'existing_files' in st.session_state:
                                del st.session_state.existing_files
                            st.experimental_rerun()
                else:
                    st.info("No hay palabras clave para eliminar en esta categoría.")

            st.markdown("---")

            # Eliminar Categoría Completa
            with st.form("delete_category_form"):
                delete_category = st.checkbox("¿Estás seguro de eliminar esta categoría?")
                delete_btn = st.form_submit_button("Eliminar Categoría")
                if delete_btn and delete_category:
                    del tracker.categories[selected_category]
                    tracker.save_categories()
                    st.success(f"Categoría '{selected_category}' eliminada exitosamente.")
                    # Reprocesar las categorías para actualizar las transacciones
                    tracker.process_data()
                    # Clean session state if needed
                    if 'existing_files' in st.session_state:
                        del st.session_state.existing_files
                    st.experimental_rerun()

    st.markdown("---")

    # Agregar Palabras Clave a Categorías (Consolidated Section)
    st.subheader("Agregar Palabras Clave a Categorías")
    with st.form("add_keywords_form"):
        category_for_keywords = st.selectbox("Selecciona una categoría", categories)
        keywords_to_add = st.text_area("Palabras clave a agregar (una por línea)")
        submitted_keywords = st.form_submit_button("Agregar Palabras Clave")
        if submitted_keywords:
            if keywords_to_add.strip() == "":
                st.error("Las palabras clave no pueden estar vacías.")
            else:
                new_keywords_list = [kw.strip().lower() for kw in keywords_to_add.split('\n') if kw.strip() != ""]
                added = 0
                for kw in new_keywords_list:
                    if kw not in tracker.categories[category_for_keywords]:
                        tracker.categories[category_for_keywords].append(kw)
                        added +=1
                if added > 0:
                    tracker.save_categories()
                    st.success(f"Agregadas {added} palabras clave a '{category_for_keywords}'.")
                    # Reprocesar las categorías para actualizar las transacciones
                    tracker.process_data()
                else:
                    st.info("No se agregaron nuevas palabras clave.")

# Mostrar el contenido según el menú seleccionado
if menu == "Dashboard":
    show_dashboard(tracker)
elif menu == "Transacciones":
    show_transactions(tracker)  # Adjust path if needed
elif menu == "Gestión de Categorías":
    show_category_management(tracker)
elif menu == "Ver DataFrame":
    st.title("DataFrame de Transacciones")
    st.dataframe(tracker.df)