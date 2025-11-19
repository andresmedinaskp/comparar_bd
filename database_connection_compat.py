"""
Módulo alternativo para versiones muy antiguas de Firebird que no soportan
las consultas estándar de metadata.
"""

import firebirdsql


def get_foreign_keys_compat(con, table_name):
    """
    Versión ultra-compatible para obtener llaves foráneas en Firebird muy antiguos.
    
    Args:
        con: Conexión a la base de datos
        table_name (str): Nombre de la tabla
        
    Returns:
        dict: Información de llaves foráneas
    """
    cur = con.cursor()
    
    # Consulta ultra-compatible para versiones muy antiguas
    try:
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
        """, (table_name,))
    except Exception as e:
        # Si todo falla, retornar diccionario vacío
        return {}
    
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
                'update_rule': 'NO ACTION',
                'delete_rule': 'NO ACTION'
            }
        
        foreign_keys[constraint_name]['fields'].append(field_name)
        foreign_keys[constraint_name]['referenced_fields'].append(referenced_field)
    
    return foreign_keys