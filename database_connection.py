"""
Módulo para manejar conexiones a bases de datos Firebird.
Contiene funciones para conectarse y obtener metadata de las bases de datos.
"""

import firebirdsql


def conectar_ruta(ruta, user, password):
    """
    Establece conexión con una base de datos Firebird.
    
    Args:
        ruta (str): Ruta del archivo de base de datos
        user (str): Usuario de la base de datos
        password (str): Contraseña del usuario
        
    Returns:
        connection: Objeto de conexión Firebird
    """
    if not ruta:
        raise ValueError("Ruta de base de datos vacía")
    return firebirdsql.connect(
        database=ruta, 
        user=user or "SYSDBA", 
        password=password or "masterkey", 
        charset="UTF8"
    )


def get_tables(con):
    """Obtiene lista de tablas de la base de datos"""
    cur = con.cursor()
    cur.execute("""
        SELECT TRIM(rdb$relation_name)
        FROM rdb$relations
        WHERE rdb$system_flag = 0 AND rdb$view_blr IS NULL
    """)
    return sorted([row[0] for row in cur.fetchall()])


def get_views(con):
    """Obtiene lista de vistas de la base de datos"""
    cur = con.cursor()
    cur.execute("""
        SELECT TRIM(rdb$relation_name)
        FROM rdb$relations
        WHERE rdb$view_blr IS NOT NULL AND rdb$system_flag = 0
    """)
    return sorted([row[0] for row in cur.fetchall()])


def get_view_definition(con, view_name):
    """Obtiene la definición SQL de una vista"""
    cur = con.cursor()
    cur.execute("""
        SELECT rdb$view_source
        FROM rdb$relations
        WHERE rdb$relation_name = ?
    """, (view_name,))
    row = cur.fetchone()
    return row[0] if row else ""


def get_generators(con):
    """Obtiene lista de generadores (sequences) de la base de datos"""
    cur = con.cursor()
    cur.execute("""
        SELECT TRIM(rdb$generator_name)
        FROM rdb$generators
        WHERE rdb$system_flag = 0
    """)
    return sorted([row[0] for row in cur.fetchall()])


def get_indexes(con, table):
    """Obtiene índices de una tabla específica (excluyendo PK)"""
    cur = con.cursor()
    cur.execute("""
        SELECT 
            TRIM(i.rdb$index_name) AS idx_name,
            i.rdb$unique_flag,
            LIST(TRIM(s.rdb$field_name)) AS fields
        FROM rdb$indices i
        LEFT JOIN rdb$index_segments s ON s.rdb$index_name = i.rdb$index_name
        WHERE i.rdb$relation_name = ?
        AND i.rdb$index_name NOT IN (
            SELECT rdb$index_name 
            FROM rdb$relation_constraints 
            WHERE rdb$relation_name = ? 
            AND rdb$constraint_type = 'PRIMARY KEY'
        )
        GROUP BY i.rdb$index_name, i.rdb$unique_flag
    """, (table, table))
    results = {}
    for r in cur.fetchall():
        results[r[0]] = {
            "unique": bool(r[1]) if r[1] is not None else False, 
            "fields": r[2] or ""
        }
    return results


def get_primary_keys(con, table):
    """Obtiene las primary keys REALES de una tabla"""
    cur = con.cursor()
    cur.execute("""
        SELECT TRIM(sg.rdb$field_name)
        FROM rdb$relation_constraints rc
        JOIN rdb$index_segments sg ON sg.rdb$index_name = rc.rdb$index_name
        WHERE rc.rdb$relation_name = ? 
        AND rc.rdb$constraint_type = 'PRIMARY KEY'
        ORDER BY sg.rdb$field_position
    """, (table,))
    return [r[0] for r in cur.fetchall()]


def get_foreign_keys(con, table):
    """
    Obtiene las llaves foráneas de una tabla.
    Versión compatible con Firebird 2.5 y superiores.
    """
    cur = con.cursor()
    
    try:
        # Intentar con consulta para versiones más recientes primero
        cur.execute("""
            SELECT 
                TRIM(rc.rdb$constraint_name) as constraint_name,
                TRIM(isf.rdb$field_name) as field_name,
                TRIM(rc.rdb$relation_name) as relation_name,
                TRIM(isc.rdb$field_name) as referenced_field
            FROM rdb$relation_constraints rc
            JOIN rdb$index_segments isf ON isf.rdb$index_name = rc.rdb$index_name
            JOIN rdb$ref_constraints refc ON refc.rdb$constraint_name = rc.rdb$constraint_name
            JOIN rdb$relation_constraints rcr ON rcr.rdb$constraint_name = refc.rdb$const_name_uq
            JOIN rdb$index_segments isc ON isc.rdb$index_name = rcr.rdb$index_name
            WHERE rc.rdb$relation_name = ? 
            AND rc.rdb$constraint_type = 'FOREIGN KEY'
            ORDER BY isf.rdb$field_position, isc.rdb$field_position
        """, (table,))
    except:
        # Si falla, usar consulta compatible con versiones antiguas
        cur.execute("""
            SELECT 
                TRIM(rc.rdb$constraint_name) as constraint_name,
                TRIM(isf.rdb$field_name) as field_name,
                TRIM(rc.rdb$relation_name) as relation_name,
                TRIM(isc.rdb$field_name) as referenced_field
            FROM rdb$relation_constraints rc
            JOIN rdb$index_segments isf ON isf.rdb$index_name = rc.rdb$index_name
            JOIN rdb$ref_constraints refc ON refc.rdb$constraint_name = rc.rdb$constraint_name
            JOIN rdb$relation_constraints rcr ON rcr.rdb$constraint_name = refc.rdb$const_name_uq
            JOIN rdb$index_segments isc ON isc.rdb$index_name = rcr.rdb$index_name
            WHERE rc.rdb$relation_name = ? 
            AND rc.rdb$constraint_type = 'FOREIGN KEY'
            ORDER BY isf.rdb$field_position, isc.rdb$field_position
        """, (table,))
    
    foreign_keys = {}
    for row in cur.fetchall():
        constraint_name = row[0]
        field_name = row[1]
        referenced_table = row[2]
        referenced_field = row[3]
        
        if constraint_name not in foreign_keys:
            foreign_keys[constraint_name] = {
                'fields': [],
                'referenced_table': referenced_table,
                'referenced_fields': [],
                'update_rule': 'NO ACTION',  # Valor por defecto
                'delete_rule': 'NO ACTION'   # Valor por defecto
            }
        
        foreign_keys[constraint_name]['fields'].append(field_name)
        foreign_keys[constraint_name]['referenced_fields'].append(referenced_field)
    
    return foreign_keys


def get_triggers(con):
    """Obtiene todos los triggers de la base de datos"""
    cur = con.cursor()
    cur.execute("""
        SELECT TRIM(rdb$trigger_name) as name, rdb$trigger_type, rdb$trigger_source,
               rdb$relation_name, rdb$trigger_sequence, rdb$trigger_inactive
        FROM rdb$triggers
        WHERE rdb$system_flag = 0
    """)
    triggers = {}
    for r in cur.fetchall():
        triggers[r[0]] = {
            "type": r[1],
            "source": r[2] or "",
            "table": r[3] or "",
            "sequence": r[4],
            "inactive": r[5]
        }
    return triggers


def get_procedures(con):
    """Obtiene todos los stored procedures de la base de datos"""
    cur = con.cursor()
    cur.execute("""
        SELECT TRIM(rdb$procedure_name) as name, rdb$procedure_source
        FROM rdb$procedures
        WHERE rdb$system_flag = 0
    """)
    procedures = {}
    for r in cur.fetchall():
        procedures[r[0]] = {"source": r[1] or ""}
    return procedures


def get_fields(con, table):
    """
    Obtiene los campos y sus propiedades de una tabla específica.
    
    Args:
        con: Conexión a la base de datos
        table (str): Nombre de la tabla
        
    Returns:
        dict: Diccionario con información de cada campo
    """
    cur = con.cursor()
    cur.execute("""
        SELECT
            TRIM(rf.rdb$field_name) AS field_name,
            COALESCE(TRIM(tt.rdb$type_name), '') AS type_name,
            f.rdb$field_length,
            f.rdb$field_precision,
            f.rdb$field_scale,
            CASE WHEN rf.rdb$null_flag = 1 THEN 'NO' ELSE 'SI' END AS nullable,
            TRIM(rf.rdb$field_source) AS domain,
            TRIM(f.rdb$default_source) AS default_source,
            CASE WHEN f.rdb$computed_blr IS NOT NULL THEN 'SI' ELSE 'NO' END AS computed,
            rf.rdb$field_position,
            TRIM(f.rdb$computed_source) AS computed_source,
            f.rdb$character_set_id,
            cs.rdb$character_set_name,
            coll.rdb$collation_name
        FROM rdb$relation_fields rf
        JOIN rdb$fields f ON f.rdb$field_name = rf.rdb$field_source
        LEFT JOIN rdb$types tt ON tt.rdb$type = f.rdb$field_type AND tt.rdb$field_name = 'RDB$FIELD_TYPE'
        LEFT JOIN rdb$character_sets cs ON cs.rdb$character_set_id = f.rdb$character_set_id
        LEFT JOIN rdb$collations coll ON coll.rdb$collation_id = f.rdb$collation_id 
            AND coll.rdb$character_set_id = f.rdb$character_set_id
        WHERE rf.rdb$relation_name = ?
        ORDER BY rf.rdb$field_position
    """, (table,))
    
    campos = {}
    for row in cur.fetchall():
        fname = row[0]
        type_name = row[1] or ""
        longitud = row[2]
        precision = row[3]
        escala = row[4]
        nullable = row[5]
        dominio = row[6]
        default = row[7]
        computed = row[8]
        posicion = row[9]
        computed_source = row[10]
        charset_id = row[11]
        charset_name = row[12]
        collation_name = row[13]
        
        # Construir tipo completo para display
        tipo_completo = type_name
        if type_name.upper() in ("CHAR", "VARCHAR") and longitud:
            tipo_completo = f"{type_name}({longitud})"
        elif type_name.upper() in ("DECIMAL", "NUMERIC") and precision is not None:
            tipo_completo = f"{type_name}({precision},{abs(escala)})" if escala != 0 else f"{type_name}({precision})"
        elif type_name.upper() == "BLOB" and longitud == 1:
            tipo_completo = "BLOB SUB_TYPE TEXT"
        elif type_name.upper() == "BLOB":
            tipo_completo = "BLOB"
            
        # Información de character set
        charset_info = ""
        if charset_name:
            charset_info = f" CHARACTER SET {charset_name}"
            if collation_name and collation_name != charset_name:
                charset_info += f" COLLATE {collation_name}"
        else:
            # Por defecto usar NONE si no está especificado
            charset_info = " CHARACTER SET NONE COLLATE NONE"
            
        campos[fname] = {
            "tipo": tipo_completo,
            "tipo_base": type_name,  # Usar el tipo base original para mapeo
            "longitud": longitud,
            "precision": precision,
            "escala": escala,
            "nullable": nullable,
            "dominio": dominio,
            "default": default,
            "computed": computed,
            "computed_source": computed_source,
            "orden": posicion,
            "charset_info": charset_info
        }
    
    return campos


def _get_generator_value(con, generator):
    """Obtiene el valor actual de un generador"""
    cur = con.cursor()
    cur.execute(f"SELECT GEN_ID({generator}, 0) FROM RDB$DATABASE")
    row = cur.fetchone()
    return row[0] if row else None