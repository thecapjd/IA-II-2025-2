import pandas as pd
import glob
import os

# --- SCRIPT PARA UNIR ARCHIVOS CSV ---

# Busca todos los archivos que terminen en .csv en la carpeta actual.
# El patrón '*.csv' encuentra todos los archivos con esa extensión.
archivos_csv = glob.glob('*.csv')

# Excluir el propio script si se guardara con .csv o el archivo final si ya existe
archivos_a_unir = [f for f in archivos_csv if f != 'CICIDS2017.csv']

if not archivos_a_unir:
    print("No se encontraron archivos CSV para unir.")
else:
    print("Se unirán los siguientes archivos:")
    for nombre in archivos_a_unir:
        print(f"- {nombre}")

    # Lista para guardar cada archivo CSV como un DataFrame
    lista_de_dataframes = []

    # Lee cada archivo CSV y lo añade a la lista
    for archivo in archivos_a_unir:
        df = pd.read_csv(archivo)
        lista_de_dataframes.append(df)

    # Concatena (une) todos los DataFrames de la lista en uno solo
    df_completo = pd.concat(lista_de_dataframes, ignore_index=True)

    # Guarda el DataFrame unido en un nuevo archivo CSV
    # index=False evita que se añada una columna extra con el índice
    nombre_archivo_final = 'CICIDS2017.csv'
    df_completo.to_csv(nombre_archivo_final, index=False)

    print(f"\n¡Éxito! ✅ Se han unido {len(lista_de_dataframes)} archivos en uno solo.")
    print(f"El archivo final se llama: '{nombre_archivo_final}'")
    print(f"Ahora puedes ejecutar el script principal del experimento.")