import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# --- CONFIGURACIÓN DE TU BASE DE DATOS ---
# Load credentials from the .env file
load_dotenv()

DB_CONFIG = {
    'host': os.getenv("DB_HOST", "127.0.0.1"),
    'port': os.getenv("DB_PORT", "3306"),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASS", ""),
    'database': os.getenv("DB_NAME", "LOCAL")
}

def insertar_movimientos_bd(df_final):
    """
    Toma el DataFrame procesado y lo inserta en la tabla bank_account_movements.
    """
    print("Iniciando conexión a la base de datos para insertar registros...")

    # Preparar la lista de tuplas para la inserción masiva
    records_to_insert = []

    # Reemplazar NaN/NaT con None para que MySQL los reciba como NULL
    df_sql = df_final.where(pd.notnull(df_final), None)

    for index, row in df_sql.iterrows():
        # Combinar Fecha_Limpia y Hora en un solo TIMESTAMP (si Hora no existe, usamos 00:00:00)
        fecha = str(row['Fecha_Limpia'])
        hora = str(row['Hora']) if row['Hora'] is not None and str(row['Hora']).strip() != '' else '00:00:00'
        movement_date = f"{fecha} {hora}"

        # Extraer y truncar datos a 45 caracteres máximo (según la definición de tu VARCHAR(45))
        concept = str(row['Concepto'])[:45] if row['Concepto'] is not None else None
        charge_or_payment = str(row['Cargo/Abono'])[:45] if row['Cargo/Abono'] is not None else None
        amount = float(row['Monto_Real']) if row['Monto_Real'] is not None else 0.0
        category = str(row['Categoria'])[:45] if row['Categoria'] is not None else None

        records_to_insert.append((movement_date, concept, charge_or_payment, amount, category))

    conexion = None
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        if conexion.is_connected():
            cursor = conexion.cursor()

            # Query de inserción (Omitimos movement_id para que el AUTO_INCREMENT haga su trabajo)
            sql_insert_query = """
                INSERT INTO bank_account_movements
                (movement_date, concept, charge_or_payment, amount, category)
                VALUES (%s, %s, %s, %s, %s)
            """

            # Usamos executemany para una inserción rápida y masiva
            cursor.executemany(sql_insert_query, records_to_insert)
            conexion.commit()

            print(f"¡Éxito! {cursor.rowcount} movimientos bancarios insertados en la base de datos.")

    except Error as e:
        print(f"Error al conectar con MySQL: {e}")
    finally:
        if conexion is not None and conexion.is_connected():
            cursor.close()
            conexion.close()
            print("Conexión a MySQL cerrada.")

def limpiar_estado_de_cuenta(archivo_entrada):
    """
    Lee, limpia, categoriza un estado de cuenta bancario y lo manda a la BD.
    """
    print(f"Procesando archivo: {archivo_entrada}...")

    # 1. Cargar el archivo
    try:
        df = pd.read_csv(archivo_entrada, encoding='latin1')
    except Exception as e:
        print("Error al leer con latin1, intentando con utf-8...")
        df = pd.read_csv(archivo_entrada, encoding='utf-8')

    # 2. Limpieza de texto general
    cols_texto = df.select_dtypes(include=['object']).columns
    for col in cols_texto:
        df[col] = df[col].astype(str).str.replace("'", "", regex=False).str.strip()

    # 3. Formateo de Fecha
    df['Fecha_Limpia'] = pd.to_datetime(df['Fecha'], format='%d%m%Y', errors='coerce').dt.strftime('%Y-%m-%d')

    # 4. Creación del Monto Real (Asegurando que cargos sean negativos y abonos positivos de forma robusta)
    # Limpiamos e Importamos como numérico absoluto
    df['Importe'] = pd.to_numeric(
        df['Importe'].astype(str).str.replace(',', '', regex=False).str.replace('$', '', regex=False).str.strip(), 
        errors='coerce'
    ).fillna(0.0)

    # Normalizamos el signo de Cargo/Abono para soportar diferentes tipos de guiones (en-dash, em-dash, etc.)
    df['Cargo/Abono'] = df['Cargo/Abono'].astype(str).str.strip().apply(lambda x: '-' if '-' in x or '–' in x or '—' in x else '+')

    # Creamos Monto_Real forzando el signo correspondiente
    df['Monto_Real'] = np.where(df['Cargo/Abono'] == '-', -df['Importe'].abs(), df['Importe'].abs())

    # 5. DICCIONARIO DE CATEGORÍAS
    categorias_personalizadas = {
        'Nómina': ['NOMINA', 'EMPLE', 'MARITE', 'HANITZIA'],
        'Comisiones e Impuestos Bancarios': ['RENTA TERMINAL', 'COMISION', 'IVA', 'SPEI'],
        'Renta y Servicios': ['RENTA', 'ADMINISTRACION', 'TELMEX', 'CFE', 'AGUA'],
        'Insumos y Proveedores': ['BELLEZA', 'PRODUCTOS', 'PROVEEDOR', 'LIVERPOOL'],
    }

    # 6. Función de categorización
    def asignar_categoria(fila):
        texto_busqueda = f"{str(fila['Concepto'])} {str(fila['Descripcion'])} {str(fila['Nombre Beneficiario'])}".upper()

        if fila['Cargo/Abono'] == '+':
            return 'Ingreso/Abono'

        for categoria, palabras_clave in categorias_personalizadas.items():
            for palabra in palabras_clave:
                if palabra in texto_busqueda:
                    return categoria

        return 'Otros Gastos Operativos'

    df['Categoria'] = df.apply(asignar_categoria, axis=1)

    # 7. Seleccionar y ordenar las columnas finales para la base de datos
    columnas_finales = [
        'Fecha_Limpia',
        'Hora',
        'Descripcion',
        'Concepto',
        'Nombre Beneficiario',
        'Cargo/Abono',
        'Importe',
        'Monto_Real',
        'Saldo',
        'Categoria'
    ]
    df_final = df[columnas_finales]

    # Imprimir resumen de la limpieza
    print("\nResumen de categorías encontradas listas para insertar:")
    print(df_final['Categoria'].value_counts())

    # 8. INSERTAR DIRECTAMENTE A LA BASE DE DATOS
    insertar_movimientos_bd(df_final)

# --- EJECUCIÓN DEL SCRIPT ---
if __name__ == "__main__":
    # Ahora solo necesitas pasarle la ruta del archivo que descargas del banco
    archivo_origen = r"G:\My Drive\Nailkery\Finanzas\2026\Abril\Facturas\20260501_MovimientosCheque.csv"

    limpiar_estado_de_cuenta(archivo_origen)