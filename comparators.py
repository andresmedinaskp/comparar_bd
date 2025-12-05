"""
Módulo con funciones para comparar objetos entre bases de datos.
Contiene los comparadores específicos para cada tipo de objeto.
"""

import re
from database_connection import get_tables, get_views, get_view_definition, get_generators
from database_connection import get_indexes, get_primary_keys, get_foreign_keys, get_fields
from database_connection import get_triggers, get_procedures, _get_generator_value


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


def normalize_for_comparison(value):
    """
    Normaliza valores para comparación, excluyendo campos RDB$XXXXX.
    
    Args:
        value: Valor a normalizar
        
    Returns:
        Valor normalizado
    """
    if value is None:
        return None
    
    if isinstance(value, dict):
        normalized = {}
        for k, v in value.items():
            if 'RDB$' not in str(k):
                normalized[k] = normalize_for_comparison(v)
        return normalized
    
    elif isinstance(value, (list, tuple)):
        return [normalize_for_comparison(item) for item in value]
    
    elif isinstance(value, str):
        if 'RDB$' in value:
            return "[VALOR_INTERNO_RDB]"
        return value
    
    else:
        return value


def agregar_fila_solo_diferencias(lista, hoja, nombre, estatus, detalle1, detalle2, sql_bd1="", sql_bd2="", diferencia=""):
    """
    Agrega filas solo si tienen diferencias.
    
    Args:
        lista: Lista donde agregar la fila
        hoja (str): Nombre de la hoja Excel
        nombre (str): Nombre del objeto
        estatus (str): Estado de la comparación
        detalle1: Detalle de BD1
        detalle2: Detalle de BD2
        sql_bd1 (str): SQL para BD1
        sql_bd2 (str): SQL para BD2
        diferencia (str): Diferencias específicas
    """
    if "DIFERENTE" in estatus or "NO EXISTE" in estatus:
        lista.append([hoja, nombre, estatus, detalle1, detalle2, sql_bd1, sql_bd2, diferencia])


def comparar_tablas(c1, c2, reporte, sql_generator):
    """Compara tablas entre dos bases de datos"""
    t1 = set(get_tables(c1))
    t2 = set(get_tables(c2))
    
    for t in sorted(t1 - t2):
        campos = get_fields(c1, t)
        sql = sql_generator.generate_create_table(t, campos, c1, "BD1")
        agregar_fila_solo_diferencias(reporte, "Tablas", t, "NO EXISTE EN BD2", t, "", sql, "")
        
    for t in sorted(t2 - t1):
        campos = get_fields(c2, t)
        sql = sql_generator.generate_create_table(t, campos, c2, "BD2")
        agregar_fila_solo_diferencias(reporte, "Tablas", t, "NO EXISTE EN BD1", "", t, "", sql)


def comparar_campos_tabla(c1, c2, tabla, reporte, sql_generator):
    """Compara campos de una tabla específica"""
    f1 = get_fields(c1, tabla)
    f2 = get_fields(c2, tabla)
    
    # DEBUG: Mostrar información de los campos
    print(f"Comparando campos de tabla: {tabla}")
    print(f"Campos BD1: {list(f1.keys())}")
    print(f"Campos BD2: {list(f2.keys())}")
    
    for c in sorted(set(f1.keys()) - set(f2.keys())):
        sql = sql_generator.generate_create_field(tabla, c, f1[c], "BD1")
        detalle_bd1 = f"Tipo: {f1[c]['tipo']}, Nullable: {f1[c]['nullable']}"
        if f1[c]['default']:
            detalle_bd1 += f", Default: {f1[c]['default']}"
        agregar_fila_solo_diferencias(reporte, f"Campos_{tabla}", c, "NO EXISTE EN BD2", detalle_bd1, "", sql, "")
        
    for c in sorted(set(f2.keys()) - set(f1.keys())):
        sql = sql_generator.generate_create_field(tabla, c, f2[c], "BD2")
        detalle_bd2 = f"Tipo: {f2[c]['tipo']}, Nullable: {f2[c]['nullable']}"
        if f2[c]['default']:
            detalle_bd2 += f", Default: {f2[c]['default']}"
        agregar_fila_solo_diferencias(reporte, f"Campos_{tabla}", c, "NO EXISTE EN BD1", "", detalle_bd2, "", sql)
        
    for c in sorted(set(f1.keys()) & set(f2.keys())):
        # Comparar propiedades relevantes, ignorando diferencias menores
        props_comparables = ['tipo', 'nullable', 'default', 'longitud', 'precision', 'escala']
        diferentes = False
        diferencias = []
        
        for key in props_comparables:
            val1 = str(f1[c].get(key, '')).strip().upper()
            val2 = str(f2[c].get(key, '')).strip().upper()
            
            # Ignorar diferencias en formato pero no en valor real
            if val1 != val2:
                # Para tipos, comparar solo el tipo base (ignorar longitud/precision en la comparación inicial)
                if key == 'tipo':
                    tipo_base1 = f1[c].get('tipo_base', '').upper()
                    tipo_base2 = f2[c].get('tipo_base', '').upper()
                    if tipo_base1 != tipo_base2:
                        diferentes = True
                        diferencias.append(f"{key}: {f1[c].get(key)} vs {f2[c].get(key)}")
                else:
                    diferentes = True
                    diferencias.append(f"{key}: {f1[c].get(key)} vs {f2[c].get(key)}")
        
        if diferentes:
            detalle_bd1 = f"Tipo: {f1[c]['tipo']}, Nullable: {f1[c]['nullable']}"
            detalle_bd2 = f"Tipo: {f2[c]['tipo']}, Nullable: {f2[c]['nullable']}"
            diferencia_texto = "; ".join(diferencias)
            
            # GENERAR SQL para modificar el campo en ambas direcciones
            # Para BD1: modificar a como está en BD2 (usando propiedades de BD2 como destino, BD1 como origen)
            sql_bd1 = sql_generator.generate_alter_field(tabla, c, f2[c], "BD1", f1[c])
            
            # Para BD2: modificar a como está en BD1 (usando propiedades de BD1 como destino, BD2 como origen)
            sql_bd2 = sql_generator.generate_alter_field(tabla, c, f1[c], "BD2", f2[c])
            
            print(f"Campo diferente encontrado: {tabla}.{c}")
            print(f"  Diferencias: {diferencia_texto}")
            print(f"  SQL BD1: {sql_bd1}")
            print(f"  SQL BD2: {sql_bd2}")
            
            agregar_fila_solo_diferencias(reporte, f"Campos_{tabla}", c, "DIFERENTE", 
                                        detalle_bd1, detalle_bd2, sql_bd1, sql_bd2, diferencia_texto)
def comparar_indices_pk(c1, c2, reporte, sql_generator):
    """Compara índices y primary keys entre bases de datos"""
    # Obtener todas las tablas de ambas bases de datos
    tablas_bd1 = set(get_tables(c1))
    tablas_bd2 = set(get_tables(c2))
    todas_las_tablas = sorted(tablas_bd1 | tablas_bd2)
    
    for tabla in todas_las_tablas:
        # Solo comparar si la tabla existe en al menos una BD
        existe_en_bd1 = tabla in tablas_bd1
        existe_en_bd2 = tabla in tablas_bd2
        
        if existe_en_bd1 and existe_en_bd2:
            # La tabla existe en ambas BD, comparar índices y PK
            i1 = get_indexes(c1, tabla)
            i2 = get_indexes(c2, tabla)
            
            for idx in sorted(set(i1.keys()) - set(i2.keys())):
                sql = sql_generator.generate_create_index(tabla, idx, i1[idx], "BD1")
                agregar_fila_solo_diferencias(reporte, f"Indices_{tabla}", idx, "NO EXISTE EN BD2", str(i1[idx]), "", sql, "")
                
            for idx in sorted(set(i2.keys()) - set(i1.keys())):
                sql = sql_generator.generate_create_index(tabla, idx, i2[idx], "BD2")
                agregar_fila_solo_diferencias(reporte, f"Indices_{tabla}", idx, "NO EXISTE EN BD1", "", str(i2[idx]), "", sql)
                
            for idx in sorted(set(i1.keys()) & set(i2.keys())):
                if i1[idx] != i2[idx]:
                    agregar_fila_solo_diferencias(reporte, f"Indices_{tabla}", idx, "DIFERENTE", str(i1[idx]), str(i2[idx]), "", "")

            # Primary Keys (solo si la tabla existe en ambas BD)
            p1 = get_primary_keys(c1, tabla)
            p2 = get_primary_keys(c2, tabla)
            
            if p1 != p2:
                sql1 = sql_generator.generate_create_primary_key(tabla, p1, "BD1") if p1 else ""
                sql2 = sql_generator.generate_create_primary_key(tabla, p2, "BD2") if p2 else ""
                agregar_fila_solo_diferencias(reporte, f"PK_{tabla}", ",".join(p1) if p1 else "(VACÍA)", "DIFERENTE", str(p1), str(p2), sql1, sql2)
        
        elif existe_en_bd1 and not existe_en_bd2:
            # La tabla solo existe en BD1, incluir sus índices y PK como faltantes en BD2
            i1 = get_indexes(c1, tabla)
            p1 = get_primary_keys(c1, tabla)
            
            for idx in i1.keys():
                sql = sql_generator.generate_create_index(tabla, idx, i1[idx], "BD1")
                agregar_fila_solo_diferencias(reporte, f"Indices_{tabla}", idx, "NO EXISTE EN BD2", str(i1[idx]), "", sql, "")
            
            if p1:
                sql = sql_generator.generate_create_primary_key(tabla, p1, "BD1")
                agregar_fila_solo_diferencias(reporte, f"PK_{tabla}", ",".join(p1), "NO EXISTE EN BD2", str(p1), "", sql, "")
        
        elif existe_en_bd2 and not existe_en_bd1:
            # La tabla solo existe en BD2, incluir sus índices y PK como faltantes en BD1
            i2 = get_indexes(c2, tabla)
            p2 = get_primary_keys(c2, tabla)
            
            for idx in i2.keys():
                sql = sql_generator.generate_create_index(tabla, idx, i2[idx], "BD2")
                agregar_fila_solo_diferencias(reporte, f"Indices_{tabla}", idx, "NO EXISTE EN BD1", "", str(i2[idx]), "", sql)
            
            if p2:
                sql = sql_generator.generate_create_primary_key(tabla, p2, "BD2")
                agregar_fila_solo_diferencias(reporte, f"PK_{tabla}", ",".join(p2), "NO EXISTE EN BD1", "", str(p2), "", sql)

def comparar_foreign_keys(c1, c2, tabla, reporte, sql_generator):
    """Compara llaves foráneas de una tabla"""
    fk1 = get_foreign_keys(c1, tabla)
    fk2 = get_foreign_keys(c2, tabla)
    
    for fk in sorted(set(fk1.keys()) - set(fk2.keys())):
        sql = sql_generator.generate_create_foreign_key(tabla, fk, fk1[fk], "BD1")
        detalle = f"REFERENCES {fk1[fk]['referenced_table']}({', '.join(fk1[fk]['referenced_fields'])})"
        agregar_fila_solo_diferencias(reporte, f"FK_{tabla}", fk, "NO EXISTE EN BD2", detalle, "", sql, "")
        
    for fk in sorted(set(fk2.keys()) - set(fk1.keys())):
        sql = sql_generator.generate_create_foreign_key(tabla, fk, fk2[fk], "BD2")
        detalle = f"REFERENCES {fk2[fk]['referenced_table']}({', '.join(fk2[fk]['referenced_fields'])})"
        agregar_fila_solo_diferencias(reporte, f"FK_{tabla}", fk, "NO EXISTE EN BD1", "", detalle, "", sql)
        
    for fk in sorted(set(fk1.keys()) & set(fk2.keys())):
        if fk1[fk] != fk2[fk]:
            agregar_fila_solo_diferencias(reporte, f"FK_{tabla}", fk, "DIFERENTE", str(fk1[fk]), str(fk2[fk]), "", "")


def comparar_triggers(c1, c2, reporte, sql_generator):
    """Compara triggers entre bases de datos"""
    tr1 = get_triggers(c1)
    tr2 = get_triggers(c2)
    
    for t in sorted(set(tr1.keys()) - set(tr2.keys())):
        sql = sql_generator.generate_create_trigger(t, tr1[t], "BD1")
        agregar_fila_solo_diferencias(reporte, "Triggers", t, "NO EXISTE EN BD2", tr1[t]['table'], "", sql, "")
        
    for t in sorted(set(tr2.keys()) - set(tr1.keys())):
        sql = sql_generator.generate_create_trigger(t, tr2[t], "BD2")
        agregar_fila_solo_diferencias(reporte, "Triggers", t, "NO EXISTE EN BD1", "", tr2[t]['table'], "", sql)
        
    for t in sorted(set(tr1.keys()) & set(tr2.keys())):
        if tr1[t] != tr2[t]:
            agregar_fila_solo_diferencias(reporte, "Triggers", t, "DIFERENTE", str(tr1[t]), str(tr2[t]), "", "")


def comparar_procedimientos(c1, c2, reporte, sql_generator):
    """Compara stored procedures entre bases de datos"""
    pr1 = get_procedures(c1)
    pr2 = get_procedures(c2)
    
    for p in sorted(set(pr1.keys()) - set(pr2.keys())):
        sql = sql_generator.generate_create_procedure(p, pr1[p], "BD1")
        agregar_fila_solo_diferencias(reporte, "Procedimientos", p, "NO EXISTE EN BD2", p, "", sql, "")
        
    for p in sorted(set(pr2.keys()) - set(pr1.keys())):
        sql = sql_generator.generate_create_procedure(p, pr2[p], "BD2")
        agregar_fila_solo_diferencias(reporte, "Procedimientos", p, "NO EXISTE EN BD1", "", p, "", sql)
        
    for p in sorted(set(pr1.keys()) & set(pr2.keys())):
        if pr1[p] != pr2[p]:
            agregar_fila_solo_diferencias(reporte, "Procedimientos", p, "DIFERENTE", str(pr1[p]), str(pr2[p]), "", "")


def comparar_vistas(c1, c2, reporte, sql_generator):
    """Compara vistas entre bases de datos"""
    v1 = set(get_views(c1))
    v2 = set(get_views(c2))
    
    for v in sorted(v1 - v2):
        definicion = get_view_definition(c1, v)
        sql = sql_generator.generate_create_view(v, definicion, "BD1")
        agregar_fila_solo_diferencias(reporte, "Vistas", v, "NO EXISTE EN BD2", v, "", sql, "")
        
    for v in sorted(v2 - v1):
        definicion = get_view_definition(c2, v)
        sql = sql_generator.generate_create_view(v, definicion, "BD2")
        agregar_fila_solo_diferencias(reporte, "Vistas", v, "NO EXISTE EN BD1", "", v, "", sql)


def comparar_generadores(c1, c2, reporte, sql_generator):
    """Compara generadores (sequences) entre bases de datos"""
    g1 = get_generators(c1)
    g2 = get_generators(c2)
    
    for g in sorted(set(g1) - set(g2)):
        try:
            v1 = _get_generator_value(c1, g)
        except Exception:
            v1 = None
        sql = sql_generator.generate_create_generator(g, v1, "BD1")
        agregar_fila_solo_diferencias(reporte, "Generadores", g, "NO EXISTE EN BD2", str(v1), "", sql, "")
        
    for g in sorted(set(g2) - set(g1)):
        try:
            v2 = _get_generator_value(c2, g)
        except Exception:
            v2 = None
        sql = sql_generator.generate_create_generator(g, v2, "BD2")
        agregar_fila_solo_diferencias(reporte, "Generadores", g, "NO EXISTE EN BD1", "", str(v2), "", sql)
        
    for g in sorted(set(g1) & set(g2)):
        try:
            v1 = _get_generator_value(c1, g)
        except Exception:
            v1 = None
        try:
            v2 = _get_generator_value(c2, g)
        except Exception:
            v2 = None
            
        if v1 != v2:
            agregar_fila_solo_diferencias(reporte, "Generadores", g, "DIFERENTE", str(v1), str(v2), "", "")

def generate_alter_field(self, table_name, campo, props, destino, props_original=None):
    """
    Genera SQL para modificar un campo existente en Firebird.
    Si la modificación no es posible, la comenta.
    
    Args:
        table_name (str): Nombre de la tabla
        campo (str): Nombre del campo
        props (dict): Nuevas propiedades del campo (destino)
        destino (str): "BD1" o "BD2"
        props_original (dict, optional): Propiedades originales del campo (origen)
        
    Returns:
        str: Sentencia ALTER TABLE (puede estar comentada)
    """
    sql_type = self._get_sql_type(props)
    
    # Verificar si la modificación es posible cuando tenemos propiedades originales
    puede_modificar = True
    razon = ""
    
    if props_original:
        puede_modificar, razon = self._puede_modificar_campo(props, props_original)
    
    sql = f"ALTER TABLE {table_name} ALTER {campo} TYPE {sql_type}"
    
    # Agregar CHARACTER SET y COLLATE solo para tipos de caracteres
    if props.get('charset_info') and not self._es_tipo_numerico(sql_type):
        charset_info = props.get('charset_info', '')
        if charset_info:
            sql += charset_info
    
    # NULL/NOT NULL
    if props['nullable'] == 'NO':
        sql += " NOT NULL"
    
    # DEFAULT
    if props['default']:
        default_value = props['default']
        if default_value.upper().startswith('DEFAULT '):
            default_value = default_value[8:]
        sql += f" DEFAULT {default_value}"
    
    sql += ";\n"
    
    # Si no se puede modificar, comentar la sentencia y agregar advertencia
    if not puede_modificar:
        sql = f"-- ⚠️ ADVERTENCIA: No se puede modificar {table_name}.{campo} - {razon}\n-- {sql}"
    
    self.emit_sql("CAMPO", sql, destino)
    return sql