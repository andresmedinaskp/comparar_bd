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

def exportar_solo_diferencias(ruta_base, filas, sql_bd1, sql_bd2, opciones_seleccionadas):
    """
    Exporta solo las diferencias a 2 archivos TXT limpios.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Filtrar filas según las opciones seleccionadas
    filas_filtradas = _filtrar_filas_por_opciones(filas, opciones_seleccionadas)
    
    # DEBUG: Mostrar información de las filas
    print(f"Total filas filtradas: {len(filas_filtradas)}")
    for i, fila in enumerate(filas_filtradas[:5]):  # Mostrar primeras 5 filas
        print(f"Fila {i}: {fila[0]}, {fila[1]}, {fila[2]}")
    
    # Exportar TXT para BD1 (lo que le falta de BD2)
    txt_path_bd1 = f"{ruta_base}_scripts_BD1_{timestamp}.txt"
    _exportar_scripts_bd1(txt_path_bd1, filas_filtradas)
    
    # Exportar TXT para BD2 (lo que le falta de BD1 + modificaciones)
    txt_path_bd2 = f"{ruta_base}_scripts_BD2_{timestamp}.txt"
    _exportar_scripts_bd2(txt_path_bd2, filas_filtradas)
    
    # Exportar TXT con SQL completo
    txt_path_sql = f"{ruta_base}_sql_completo_{timestamp}.txt"
    _exportar_txt_sql(txt_path_sql, sql_bd1, sql_bd2)

    return txt_path_bd1, txt_path_bd2, txt_path_sql

def _filtrar_filas_por_opciones(filas, opciones):
    """
    Filtra las filas según las opciones seleccionadas por el usuario.
    
    Args:
        filas (list): Lista completa de diferencias
        opciones (dict): Opciones seleccionadas
        
    Returns:
        list: Filas filtradas
    """
    if not opciones:
        return filas  # Si no hay opciones, retornar todo
    
    filas_filtradas = []
    
    # Mapeo de tipos de objeto a las opciones (MÁS ESPECÍFICO)
    mapeo_tipos = {
        'Tablas': 'tablas',
        'Campos_': 'campos',
        'Indices_': 'indices', 
        'PK_': 'pk',
        'FK_': 'fk',
        'Triggers': 'triggers',
        'Procedimientos': 'procedimientos',
        'Vistas': 'vistas',
        'Generadores': 'generadores'
    }
    
    for fila in filas:
        tipo_objeto = fila[0]
        
        # Verificar si este tipo de objeto fue seleccionado
        incluir = False
        
        for prefijo, opcion in mapeo_tipos.items():
            if tipo_objeto.startswith(prefijo):
                if opciones.get(opcion, False):
                    incluir = True
                break
        
        # Si no coincide con ningún prefijo conocido, incluir por defecto
        if not any(tipo_objeto.startswith(prefijo) for prefijo in mapeo_tipos.keys()):
            incluir = True
        
        if incluir:
            filas_filtradas.append(fila)
    
    return filas_filtradas

def _exportar_scripts_bd1(ruta, filas):
    """
    Exporta scripts para BD1: Solo objetos que NO EXISTEN en BD1 pero SÍ en BD2
    """
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write("-- SCRIPTS PARA BD1 (PRINCIPAL)\n")
        f.write("-- Agregar lo que falta en BD1 pero existe en BD2\n")
        f.write("-- Ejecutar en orden en BD1\n\n")
        
        # Recolectar todos los scripts para BD1
        todos_scripts = []
        
        for fila in filas:
            tipo_objeto = fila[0]
            nombre_objeto = fila[1]
            estatus = fila[2]
            sql_bd1 = fila[5] or ""  # SQL para BD1 (columna 5)
            sql_bd2 = fila[6] or ""  # SQL para BD2 (columna 6)
            
            print(f"Procesando BD1 - {tipo_objeto} {nombre_objeto}: {estatus}")
            
            # SOLO PARA BD1: Objetos que NO EXISTEN en BD1 pero SÍ en BD2
            if "NO EXISTE EN BD1" in estatus:
                sql_usar = sql_bd2  # Usar SQL de BD2 para crear en BD1
                if sql_usar.strip():
                    sql_limpio = _limpiar_sql(sql_usar)
                    if sql_limpio:
                        # Aplicar CREATE OR ALTER si es procedimiento, vista o trigger
                        if any(tipo in tipo_objeto for tipo in ['Procedimientos', 'Vistas', 'Triggers']):
                            sql_limpio = sql_limpio.replace('CREATE PROCEDURE', 'CREATE OR ALTER PROCEDURE')
                            sql_limpio = sql_limpio.replace('CREATE VIEW', 'CREATE OR ALTER VIEW')
                            sql_limpio = sql_limpio.replace('CREATE TRIGGER', 'CREATE OR ALTER TRIGGER')
                        
                        todos_scripts.append(sql_limpio)
                        print(f"  -> AGREGADO: {tipo_objeto} {nombre_objeto}")
            
            # ELIMINADO: No procesar objetos "DIFERENTES" en BD1
            # Los ALTER TABLE solo deben ir a BD2
        
        # Escribir todos los scripts
        if todos_scripts:
            for sql in todos_scripts:
                f.write(sql + "\n\n")
            f.write(f"-- Total scripts: {len(todos_scripts)}\n")
        else:
            f.write("-- BD1 ya tiene todos los objetos de BD2\n")
        
        print(f"SCRIPTS BD1 GENERADOS: {len(todos_scripts)}")

def _exportar_scripts_bd2(ruta, filas):
    """
    Exporta scripts para BD2: 
    - Lo que le falta pero sí está en BD1
    - Modificaciones para quedar igual a BD1
    """
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write("-- SCRIPTS PARA BD2\n")
        f.write("-- 1. Agregar lo que falta en BD2 pero existe en BD1\n") 
        f.write("-- 2. Modificar objetos para quedar igual a BD1\n")
        f.write("-- Ejecutar en orden en BD2\n\n")
        
        # Recolectar todos los scripts para BD2
        todos_scripts = []
        
        for fila in filas:
            tipo_objeto = fila[0]
            nombre_objeto = fila[1]
            estatus = fila[2]
            sql_bd1 = fila[5] or ""  # CORRECCIÓN: SQL para BD1 (columna 5)
            sql_bd2 = fila[6] or ""  # CORRECCIÓN: SQL para BD2 (columna 6)
            
            print(f"Procesando BD2 - {tipo_objeto} {nombre_objeto}: {estatus}")
            print(f"  SQL BD1 disponible: {bool(sql_bd1.strip())}")
            print(f"  SQL BD2 disponible: {bool(sql_bd2.strip())}")
            
            # Para BD2: Objetos que NO EXISTEN en BD2 pero SÍ en BD1
            if "NO EXISTE EN BD2" in estatus:
                sql_usar = sql_bd1  # Usar SQL de BD1 para crear en BD2
                if sql_usar.strip():
                    sql_limpio = _limpiar_sql(sql_usar)
                    if sql_limpio:
                        # Aplicar CREATE OR ALTER si es procedimiento, vista o trigger
                        if any(tipo in tipo_objeto for tipo in ['Procedimientos', 'Vistas', 'Triggers']):
                            sql_limpio = sql_limpio.replace('CREATE PROCEDURE', 'CREATE OR ALTER PROCEDURE')
                            sql_limpio = sql_limpio.replace('CREATE VIEW', 'CREATE OR ALTER VIEW')
                            sql_limpio = sql_limpio.replace('CREATE TRIGGER', 'CREATE OR ALTER TRIGGER')
                        
                        todos_scripts.append(sql_limpio)
                        print(f"  -> AGREGADO: {tipo_objeto} {nombre_objeto}")
            
            # Para BD2: También incluir objetos DIFERENTES (modificaciones desde BD1)
            elif "DIFERENTE" in estatus:
                sql_usar = sql_bd1  # Usar SQL de BD1 para modificar BD2
                if sql_usar.strip():
                    sql_limpio = _limpiar_sql(sql_usar)
                    if sql_limpio:
                        if any(tipo in tipo_objeto for tipo in ['Procedimientos', 'Vistas', 'Triggers']):
                            sql_limpio = sql_limpio.replace('CREATE PROCEDURE', 'CREATE OR ALTER PROCEDURE')
                            sql_limpio = sql_limpio.replace('CREATE VIEW', 'CREATE OR ALTER VIEW') 
                            sql_limpio = sql_limpio.replace('CREATE TRIGGER', 'CREATE OR ALTER TRIGGER')
                        
                        todos_scripts.append(sql_limpio)
                        print(f"  -> MODIFICACION: {tipo_objeto} {nombre_objeto}")
        
        # Escribir todos los scripts
        if todos_scripts:
            for sql in todos_scripts:
                f.write(sql + "\n\n")
            f.write(f"-- Total scripts: {len(todos_scripts)}\n")
        else:
            f.write("-- BD2 ya está sincronizada con BD1\n")
        
        print(f"SCRIPTS BD2 GENERADOS: {len(todos_scripts)}")

def _clasificar_script(tipo_objeto, sql_limpio, scripts_tablas, scripts_campos, scripts_indices,
                      scripts_pk, scripts_fk, scripts_generadores, scripts_procedimientos, 
                      scripts_vistas, scripts_triggers):
    """
    Clasifica el script en la categoría correspondiente.
    """
    # Aplicar CREATE OR ALTER para procedimientos, vistas y triggers
    if "Procedimientos" in tipo_objeto:
        sql_limpio = sql_limpio.replace('CREATE PROCEDURE', 'CREATE OR ALTER PROCEDURE')
        scripts_procedimientos.append(sql_limpio)
    
    elif "Vistas" in tipo_objeto:
        sql_limpio = sql_limpio.replace('CREATE VIEW', 'CREATE OR ALTER VIEW')
        scripts_vistas.append(sql_limpio)
    
    elif "Triggers" in tipo_objeto:
        sql_limpio = sql_limpio.replace('CREATE TRIGGER', 'CREATE OR ALTER TRIGGER')
        scripts_triggers.append(sql_limpio)
    
    elif "Tablas" in tipo_objeto:
        scripts_tablas.append(sql_limpio)
    
    elif "Campos_" in tipo_objeto:
        scripts_campos.append(sql_limpio)
    
    elif "Indices_" in tipo_objeto:
        scripts_indices.append(sql_limpio)
    
    elif "PK_" in tipo_objeto:
        scripts_pk.append(sql_limpio)
    
    elif "FK_" in tipo_objeto:
        scripts_fk.append(sql_limpio)
    
    elif "Generadores" in tipo_objeto:
        scripts_generadores.append(sql_limpio)       

def _limpiar_sql(sql_completo):
    """
    Limpia el SQL, manteniendo solo lo ejecutable.
    """
    if not sql_completo:
        return ""
    
    # Si el SQL ya está limpio, mantenerlo
    if 'CREATE ' in sql_completo or 'ALTER ' in sql_completo or 'SET ' in sql_completo:
        # Solo dividir en líneas si es necesario para limpiar
        lines = sql_completo.split('\n')
        sql_limpio = []
        
        for line in lines:
            line = line.strip()
            # Eliminar líneas que contengan solo propiedades de campos sin SQL
            if (line and 
                not line.startswith('/* Tabla:') and 
                not line.startswith('/* Primary keys') and
                not line.startswith('Tipo:') and
                not line.startswith('Nullable:') and
                not line.startswith('Default:')):
                sql_limpio.append(line)
        
        return '\n'.join(sql_limpio)
    
    return sql_completo.strip()

def _extraer_sql_ejecutable(sql_completo):
    """
    Extrae solo el SQL ejecutable, eliminando comentarios innecesarios y texto extra.
    
    Args:
        sql_completo (str): SQL con posibles comentarios y texto extra
        
    Returns:
        str: SQL limpio y ejecutable
    """
    if not sql_completo:
        return ""
    
    lines = sql_completo.split('\n')
    sql_limpio = []
    
    for line in lines:
        line = line.strip()
        
        # Mantener solo líneas que contengan SQL ejecutable
        if (line.startswith('CREATE') or 
            line.startswith('ALTER') or 
            line.startswith('DROP') or 
            line.startswith('SET') or 
            line.startswith('UPDATE') or
            line.startswith('INSERT') or
            line.startswith('DELETE') or
            (line.startswith('/*') and '*/' in line) or  # Comentarios cortos
            line.endswith(';')):
            
            # Limpiar comentarios extensos pero mantener los esenciales
            if line.startswith('/*') and len(line) > 100:
                # Comentario muy largo, omitir
                continue
                
            sql_limpio.append(line)
    
    return '\n'.join(sql_limpio)

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