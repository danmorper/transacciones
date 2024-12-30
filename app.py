#app.py
import streamlit as st
import json
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Optional
import os
import zipfile
import io

from modules.WiseTracker import WiseTracker  # Asegúrate de que este módulo exista y esté correctamente definido

# Configuración de la página
st.set_page_config(page_title="Rastreador de Finanzas Personales", layout="wide")

CSV_PATH = "transacciones.csv"

# Función para inicializar el rastreador y almacenar en el estado de sesión
@st.cache_resource
def initialize_tracker():
    EXCHANGE_RATES = {
        'EUR': 1.0,    # Divisa base
        'USD': 0.92,   # 1 USD = 0.92 EUR
        'GBP': 1.14,   # 1 GBP = 1.14 EUR
        'HUF': 0.0024, # 1 HUF = 0.0024 EUR
        'DKK': 0.13,   # 1 DKK = 0.13 EUR
        'RSD': 0.0085  # 1 RSD = 0.0085 EUR
        # Puedes añadir más divisas según sea necesario
    }
    CATEGORIES_PATH = "clasificacion.json"
    tracker = WiseTracker(categories_path=CATEGORIES_PATH, 
                          exchange_rates=EXCHANGE_RATES, 
                          base_currency='EUR')
    return tracker

# Inicializar el rastreador
tracker = initialize_tracker()

# Función para guardar los datos mensuales
def save_monthly_data(tracker: WiseTracker, output_dir: str):
     # **Nueva Sección: Guardar Datos Mensuales**
    st.sidebar.subheader("Guardar Datos Mensuales")
    save_button = st.sidebar.button("Guardar Datos Mensuales")
    output_dir = "monthly_data"
    if save_button:
        try:            
            # Ejecutar la función para guardar datos mensuales
            tracker.save_monthly_data(output_dir=output_dir)
            st.success(f"Datos mensuales guardados en el directorio '{output_dir}'.")
        except Exception as e:
            st.sidebar.error(f"Error al guardar los datos mensuales: {e}")
    elif save_button:
        st.sidebar.info("No se generaron nuevos archivos CSV.")

# Función para cargar los datos mensuales
def load_monthly_data(tracker: WiseTracker, input_dir: str):
    st.sidebar.markdown("---")
    # **Nueva Sección: Cargar Datos Mensuales**
    st.sidebar.subheader("Cargar Datos Mensuales")
    load_button = st.sidebar.button("Cargar Datos Mensuales")
    input_dir = "monthly_data"
    if load_button:
        try:
            # Ejecutar la función para cargar datos mensuales
            tracker.load_monthly_data(input_dir=input_dir)
            st.sidebar.success(f"Datos mensuales cargados desde el directorio '{input_dir}'.")
        except Exception as e:
            st.sidebar.error(f"Error al cargar los datos mensuales: {e}")
    elif load_button:
        st.sidebar.info("No se cargaron nuevos archivos CSV.")

# Función para guardar el json de categorías
def save_categories(tracker: WiseTracker):
    st.sidebar.markdown("---")

    # **Nueva Sección: Descargar clasificacion.json Actualizado**
    st.sidebar.subheader("Descargar clasificacion.json Actualizado")
    try:
        with open(tracker.categories_path, "r", encoding='utf-8') as f:
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
menu = st.sidebar.radio("Ir a", ["Dashboard", "Transacciones", "Gestión de Categorías", "Ver DataFrame"])

save_monthly_data(tracker, "monthly_data")
load_monthly_data(tracker, "monthly_data")
save_categories(tracker)

# Función para mostrar el Dashboard
def show_dashboard(tracker: WiseTracker):
    st.title("Dashboard Financiero")

    # Calcular el neto por mes
    try:
        neto_mensual = tracker.net_amount_per_month()
        # st.success("Neto por Mes calculado correctamente.")
    except ValueError as ve:
        st.error(str(ve))
        neto_mensual = pd.Series(dtype=float)

    # Calcular los gastos por categoría y mes
    try:
        gastos_categoria = tracker.expenses_per_category_per_month()
        # st.success("Gastos por Categoría y Mes calculados correctamente.")
    except ValueError as ve:
        st.error(str(ve))
        gastos_categoria = pd.DataFrame()

    # Mostrar las columnas disponibles para depuración
    # st.markdown("### Columnas Disponibles en el DataFrame")
    # st.write(tracker.df.columns.tolist())

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
        fig, ax = plt.subplots(figsize=(12, 8))
        gastos_categoria.plot(kind='bar', stacked=True, ax=ax)
        ax.set_title('Gastos por Categoría y Mes (EUR)')
        ax.set_xlabel('Mes')
        ax.set_ylabel('Monto Gastado (EUR)')
        ax.legend(title='Categoría', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.write("No hay datos para mostrar el gráfico de gastos.")

# Función para mostrar las Transacciones
def show_transactions(tracker: WiseTracker, csv_path: str):
    st.title("Transacciones")

    # Mostrar las transacciones en una tabla
    st.subheader("Revisar y Clasificar Transacciones")

    # Asegurarse de que las columnas necesarias existan
    display_columns = ['Target name', 'Created on', 'Target amount (after fees)', 
                       'Target currency', 'Direction', 'Categoría', 'Amount in EUR']
    for col in display_columns:
        if col not in tracker.df.columns:
            tracker.df[col] = ''

    # Convertir 'Created on' a datetime si no lo está
    if not pd.api.types.is_datetime64_any_dtype(tracker.df['Created on']):
        tracker.df['Created on'] = pd.to_datetime(tracker.df['Created on'], errors='coerce')

    # Obtener el rango de fechas
    min_date = tracker.df['Created on'].min()
    max_date = tracker.df['Created on'].max()

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
    mask = (tracker.df['Created on'].dt.date >= start_date) & (tracker.df['Created on'].dt.date <= end_date)
    filtered_df = tracker.df.loc[mask, display_columns].copy()

    st.markdown("### Transacciones Filtradas")
    st.write(f"Mostrando transacciones desde **{start_date}** hasta **{end_date}**.")

    # Mostrar el DataFrame editable
    edited_df = st.data_editor(
        filtered_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Direction": st.column_config.SelectboxColumn(
                "Direction",
                options=["IN", "OUT"],
                default="OUT",
            ),
            "Categoría": st.column_config.SelectboxColumn(
                "Categoría",
                options=list(tracker.categories.keys()) + ["Otros"],
            ),
            "Target name": st.column_config.TextColumn("Target name"),
            "Created on": st.column_config.DateColumn("Created on"),
            "Target amount (after fees)": st.column_config.NumberColumn("Target amount (after fees)"),
            "Target currency": st.column_config.TextColumn("Target currency"),
            "Amount in EUR": st.column_config.NumberColumn("Amount in EUR", disabled=True),
        }
    )

    # Botón para guardar cambios
    if st.button("Guardar Cambios"):
        try:
            # Actualizar el DataFrame original con los cambios realizados en el filtro
            # Excluir 'Amount in EUR' ya que es calculado
            tracker.df.loc[mask, display_columns[:-1]] = edited_df[display_columns[:-1]]
            # Guardar cambios en el CSV, excluyendo 'Amount in EUR'
            # Asumiendo que 'Año_Mes' y 'Amount in EUR' son columnas calculadas y no se guardan en el CSV
            columns_to_save = [col for col in display_columns if col != 'Amount in EUR']
            tracker.df.to_csv(csv_path, columns=columns_to_save, index=False)
            st.success("Cambios guardados exitosamente en el archivo CSV.")
            # Reprocesar los datos para actualizar las categorías y montos
            tracker.process_data()
            # Resetear el estado para permitir re-procesamiento si es necesario
            st.session_state.processed = False
        except Exception as e:
            st.error(f"Error al guardar los cambios: {e}")

    # # Agregar una sección de resumen para depuración
    # st.markdown("### Resumen de Transacciones")
    # num_out = tracker.df[tracker.df['Direction'].str.upper() == 'OUT'].shape[0]
    # num_in = tracker.df[tracker.df['Direction'].str.upper() == 'IN'].shape[0]
    # st.write(f"**Total IN:** {num_in}")
    # st.write(f"**Total OUT:** {num_out}")

    # Categorías presentes en gastos
    st.markdown("### Categorías de Gastos")
    categorias_out = tracker.df.loc[tracker.df['Direction'].str.upper() == 'OUT', 'Categoría'].unique()
    categorias_out = [cat for cat in categorias_out if cat != "Otros" and pd.notnull(cat)]
    print(categorias_out)
    if len(categorias_out) > 0:
        st.write(categorias_out)
        st.write(f"Categorías presentes en gastos: {', '.join(categorias_out)}")
    else:
        st.write("No hay categorías asignadas a gastos 'OUT'.")

# Función para mostrar la Gestión de Categorías
def show_category_management(tracker: WiseTracker):
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
                    # Limpiar archivos generados anteriores si existen
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
                                # Limpiar archivos generados anteriores si existen
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
                            # Limpiar archivos generados anteriores si existen
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
                    # Limpiar archivos generados anteriores si existen
                    if 'existing_files' in st.session_state:
                        del st.session_state.existing_files
                    st.experimental_rerun()

    st.markdown("---")

    # Agregar Palabras Clave a Categorías
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
    show_transactions(tracker, CSV_PATH)
elif menu == "Gestión de Categorías":
    show_category_management(tracker)

# Mostrar el DataFrame si se selecciona
if menu == "Ver DataFrame":
    st.title("DataFrame de Transacciones")
    st.write(tracker.df)