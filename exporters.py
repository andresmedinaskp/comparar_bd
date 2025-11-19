"""
Módulo para exportar resultados a diferentes formatos.
Contiene funciones para generar archivos TXT con las diferencias y SQL.
"""

import re
from datetime import datetime

def clean_sheet_name(name):
    """
    Limpia el nombre para que sea válido como nombre de hoja Excel.
    
    Args:
        name (str): Nombre original
        
    Returns:
        str: Nombre limpio
    """
    invalid_chars = r'[\\/*?\[\]:]'
    cleaned = re.sub(invalid_chars, '_', name)
    
    if len(cleaned) > 31:
        cleaned = cleaned[:31]
    
    cleaned = cleaned.strip("'")
    return cleaned

def exportar_solo_diferencias(ruta_base, filas, sql_bd1, sql_bd2):
    """
    Exporta solo las diferencias a archivos TXT separados por BD.
    
    Args:
        ruta_base (str): Ruta base para los archivos
        filas (list): Lista de diferencias encontradas
        sql_bd1 (str): SQL para BD1
        sql_bd2 (str): SQL para BD2
        
    Returns:
        tuple: (ruta_txt_bd1, ruta_txt_bd2)
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Separar diferencias por BD
    diferencias_bd1 = [f for f in filas if f[5] and not f[6]]  # Solo tiene SQL para BD1
    diferencias_bd2 = [f for f in filas if f[6] and not f[5]]  # Solo tiene SQL para BD2
    diferencias_comunes = [f for f in filas if f[5] and f[6]]  # Tiene SQL para ambas
    
    # Exportar TXT con diferencias separadas
    txt_path_bd1 = f"{ruta_base}_BD1_diferencias_{timestamp}.txt"
    _exportar_txt_diferencias(txt_path_bd1, diferencias_bd1 + diferencias_comunes, "BD1")
    
    txt_path_bd2 = f"{ruta_base}_BD2_diferencias_{timestamp}.txt"
    _exportar_txt_diferencias(txt_path_bd2, diferencias_bd2 + diferencias_comunes, "BD2")
    
    # Exportar TXT con SQL de ambas BD
    txt_path_sql = f"{ruta_base}_sql_completo_{timestamp}.txt"
    _exportar_txt_sql(txt_path_sql, sql_bd1, sql_bd2)

    return txt_path_bd1, txt_path_bd2, txt_path_sql

def _exportar_txt_diferencias(ruta, filas, bd_destino):
    """
    Exporta las diferencias a un archivo TXT específico para una BD.
    
    Args:
        ruta (str): Ruta del archivo TXT
        filas (list): Lista de diferencias
        bd_destino (str): "BD1" o "BD2" - indica para qué BD es el reporte
    """
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"REPORTE DE DIFERENCIAS - {bd_destino}\n")
        f.write("=" * 80 + "\n\n")
        
        # Agrupar por tipo de objeto
        diferencias_por_tipo = {}
        for fila in filas:
            tipo_objeto = fila[0]  # La primera columna es el tipo (Tablas, Campos, etc.)
            if tipo_objeto not in diferencias_por_tipo:
                diferencias_por_tipo[tipo_objeto] = []
            diferencias_por_tipo[tipo_objeto].append(fila[1:])  # El resto de las columnas
        
        # Escribir diferencias por tipo
        for tipo, items in sorted(diferencias_por_tipo.items()):
            f.write(f"\n{'='*60}\n")
            f.write(f"{tipo.upper()}\n")
            f.write(f"{'='*60}\n\n")
            
            for item in items:
                nombre = item[0]  # Nombre del objeto
                estatus = item[1]  # Estatus
                detalle_bd1 = item[2] or ""
                detalle_bd2 = item[3] or ""
                sql_bd1 = item[4] or ""
                sql_bd2 = item[5] or ""
                diferencias = item[6] or ""
                
                f.write(f"OBJETO: {nombre}\n")
                f.write(f"ESTADO: {estatus}\n")
                
                if detalle_bd1:
                    f.write(f"BD1: {detalle_bd1}\n")
                if detalle_bd2:
                    f.write(f"BD2: {detalle_bd2}\n")
                if diferencias:
                    f.write(f"DIFERENCIAS: {diferencias}\n")
                
                # Mostrar SQL según la BD destino
                if bd_destino == "BD1" and sql_bd2:
                    f.write(f"SQL PARA BD2:\n{sql_bd2}\n")
                elif bd_destino == "BD2" and sql_bd1:
                    f.write(f"SQL PARA BD1:\n{sql_bd1}\n")
                
                f.write("-" * 60 + "\n\n")

def _exportar_txt_sql(ruta, sql_bd1, sql_bd2):
    """
    Exporta el SQL generado a un archivo TXT.
    
    Args:
        ruta (str): Ruta del archivo TXT
        sql_bd1 (str): SQL para BD1
        sql_bd2 (str): SQL para BD2
    """
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SQL PARA BD2 (Crear objetos faltantes de BD1)\n")
        f.write("=" * 80 + "\n\n")
        f.write(sql_bd1)
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("SQL PARA BD1 (Crear objetos faltantes de BD2)\n")
        f.write("=" * 80 + "\n\n")
        f.write(sql_bd2)