"""
Módulo para generar sentencias SQL válidas para Firebird.
Contiene la clase SQLGenerator que crea sentencias CREATE para todos los objetos.
"""

from database_connection import get_primary_keys, get_foreign_keys
from collections import defaultdict, deque

class SQLGenerator:
    """
    Generador de sentencias SQL para crear objetos de base de datos Firebird.
    """
    
    def __init__(self, worker_signals=None):
        """
        Inicializa el generador de SQL.
        
        Args:
            worker_signals: Señales para comunicación con el hilo principal
        """
        self.worker_signals = worker_signals
        self.sql_bd1 = ""  # SQL para BD2 (crear objetos de BD1)
        self.sql_bd2 = ""  # SQL para BD1 (crear objetos de BD2)
        
        # Almacenar SQL por tipo para ordenamiento posterior
        self.sql_objects_bd1 = defaultdict(list)
        self.sql_objects_bd2 = defaultdict(list)
        
        # Orden de creación (de menos a más dependiente)
        self.creation_order = [
            'GENERADOR',
            'TABLA', 
            'CAMPO',
            'PRIMARY_KEY',
            'INDICE',
            'FOREIGN_KEY',
            'VISTA',
            'PROCEDIMIENTO',
            'TRIGGER'
        ]
    
    def emit_sql(self, tipo, sql, destino):
        """
        Emite SQL a través de las señales y lo acumula internamente por tipo.
        
        Args:
            tipo (str): Tipo de objeto (TABLA, CAMPO, etc.)
            sql (str): Sentencia SQL generada
            destino (str): "BD1" o "BD2"
        """
        if self.worker_signals:
            self.worker_signals.sql_generated.emit(tipo, sql)
        
        if destino == "BD1":
            self.sql_objects_bd1[tipo].append(sql)
        elif destino == "BD2":
            self.sql_objects_bd2[tipo].append(sql)
    
    def _build_final_sql(self, sql_objects):
        """
        Construye el SQL final en el orden correcto.
        
        Args:
            sql_objects (dict): Diccionario con SQL por tipo
            
        Returns:
            str: SQL final ordenado
        """
        final_sql = ""
        
        # Agregar en el orden de creación
        for object_type in self.creation_order:
            if object_type in sql_objects:
                for sql in sql_objects[object_type]:
                    final_sql += sql + "\n\n"
        
        return final_sql
    
    def get_sql_bd1(self):
        """Obtiene todo el SQL acumulado para BD1 en orden correcto"""
        return self._build_final_sql(self.sql_objects_bd1)
    
    def get_sql_bd2(self):
        """Obtiene todo el SQL acumulado para BD2 en orden correcto"""
        return self._build_final_sql(self.sql_objects_bd2)
    
    # El resto de las funciones generate_* permanecen igual...
    def _get_sql_type(self, props):
        """
        Convierte las propiedades de campo a tipo SQL válido para Firebird.
        """
        tipo_base = props['tipo_base'].upper() if props.get('tipo_base') else ''
        tipo_completo = props['tipo'].upper() if props.get('tipo') else tipo_base
        
        # Si ya tenemos un tipo completo, usarlo (puede incluir longitud/precision)
        if '(' in tipo_completo and ')' in tipo_completo:
            return tipo_completo
        
        longitud = props.get('longitud')
        precision = props.get('precision')
        escala = props.get('escala')
        
        # Mapear tipos de Firebird
        type_mapping = {
            'LONG': 'INTEGER',
            'SHORT': 'SMALLINT',
            'INT64': 'BIGINT',
            'QUAD': 'BIGINT',
            'VARYING': 'VARCHAR',
            'FLOAT': 'FLOAT',
            'DOUBLE': 'DOUBLE PRECISION',
            'TIMESTAMP': 'TIMESTAMP',
            'DATE': 'DATE',
            'TIME': 'TIME',
            'TEXT': 'BLOB SUB_TYPE TEXT'
        }
        
        # Aplicar mapeo si es necesario
        if tipo_base in type_mapping:
            tipo_base = type_mapping[tipo_base]
        elif tipo_completo in type_mapping:
            tipo_base = type_mapping[tipo_completo]
        else:
            tipo_base = tipo_completo or tipo_base
        
        # Construir el tipo con longitud/precision si es necesario
        if tipo_base in ('CHAR', 'VARCHAR', 'CHARACTER VARYING'):
            if longitud and longitud > 0:
                return f"{tipo_base}({longitud})"
            else:
                return f"{tipo_base}(1)"  # Longitud por defecto
        elif tipo_base in ('DECIMAL', 'NUMERIC'):
            if precision is not None:
                if escala and escala != 0:
                    return f"{tipo_base}({precision},{abs(escala)})"
                else:
                    return f"{tipo_base}({precision})"
            else:
                return tipo_base
        elif tipo_base == 'BLOB':
            if longitud == 1:
                return "BLOB SUB_TYPE TEXT"
            else:
                return "BLOB"
        else:
            return tipo_base
    
    def generate_create_table(self, table_name, campos, conexion, destino):
        """
        Genera SQL LIMPIO para crear una tabla SIN primary key.
        La PK se agregará después con ALTER TABLE.
        """
        # Obtener PK pero NO incluirla inline
        pk = get_primary_keys(conexion, table_name)
        
        sql = f"CREATE TABLE {table_name} (\n"
        field_defs = []
        
        for campo, props in campos.items():
            sql_type = self._get_sql_type(props)
            
            field_def = f"    {campo} {sql_type}"
            
            # CHARACTER SET y COLLATE
            charset_info = props.get('charset_info', '')
            if charset_info:
                field_def += charset_info
                
            # NULL/NOT NULL
            if props['nullable'] == 'NO':
                field_def += " NOT NULL"
                
            # DEFAULT
            if props['default']:
                default_value = props['default']
                if default_value.upper().startswith('DEFAULT '):
                    default_value = default_value[8:]
                field_def += f" DEFAULT {default_value}"
                
            # COMPUTED BY
            if props['computed'] == 'SI' and props['computed_source']:
                computed_expr = props['computed_source']
                if computed_expr.upper().startswith('COMPUTED BY '):
                    computed_expr = computed_expr[12:]
                field_def += f" COMPUTED BY ({computed_expr})"
                
            field_defs.append(field_def)
        
        sql += ",\n".join(field_defs)
        
        # NO incluir PRIMARY KEY inline - se agregará después
        sql += "\n);\n"
        
        self.emit_sql("TABLA", sql, destino)
        
        # Generar ALTER TABLE para PK por separado
        if pk:
            pk_sql = self.generate_create_primary_key(table_name, pk, destino)
            return sql + "\n" + pk_sql
        
        return sql
    
    def generate_create_field(self, table_name, campo, props, destino):
        """
        Genera SQL para agregar un campo a una tabla existente.
        
        Args:
            table_name (str): Nombre de la tabla
            campo (str): Nombre del campo
            props (dict): Propiedades del campo
            destino (str): "BD1" o "BD2"
            
        Returns:
            str: Sentencia ALTER TABLE
        """
        sql_type = self._get_sql_type(props)
        
        # Construir la definición completa del campo
        sql = f"ALTER TABLE {table_name} ADD {campo} {sql_type}"
        
        # Agregar CHARACTER SET y COLLATE si están especificados
        charset_info = props.get('charset_info', '')
        if charset_info:
            sql += charset_info
        else:
            # Si no hay charset info, usar CHARACTER SET NONE COLLATE NONE por defecto
            sql += " CHARACTER SET NONE COLLATE NONE"
        
        if props['nullable'] == 'NO':
            sql += " NOT NULL"
            
        if props['default']:
            default_value = props['default']
            if default_value.upper().startswith('DEFAULT '):
                default_value = default_value[8:]
            sql += f" DEFAULT {default_value}"
            
        sql += ";\n"
        
        self.emit_sql("CAMPO", sql, destino)
        return sql
    
    def generate_create_index(self, table_name, index_name, index_info, destino):
        """
        Genera SQL para crear un índice.
        
        Args:
            table_name (str): Nombre de la tabla
            index_name (str): Nombre del índice
            index_info (dict): Información del índice
            destino (str): "BD1" o "BD2"
            
        Returns:
            str: Sentencia CREATE INDEX
        """
        unique = "UNIQUE " if index_info['unique'] else ""
        
        # Limpiar nombre si es interno
        if index_name.startswith('RDB$'):
            fields = index_info['fields'].split(',')[0] if ',' in index_info['fields'] else index_info['fields']
            index_name = f"IDX_{table_name}_{fields}"
        
        sql = f"CREATE {unique}INDEX {index_name} ON {table_name} ({index_info['fields']});\n"
        
        self.emit_sql("INDICE", sql, destino)
        return sql
    
    def generate_create_primary_key(self, table_name, pk_fields, destino):
        """
        Genera SQL para crear primary key.
        
        Args:
            table_name (str): Nombre de la tabla
            pk_fields (list): Lista de campos de la PK
            destino (str): "BD1" o "BD2"
            
        Returns:
            str: Sentencia ALTER TABLE o string vacío
        """
        if pk_fields:
            sql = f"ALTER TABLE {table_name} ADD CONSTRAINT PK_{table_name} PRIMARY KEY ({', '.join(pk_fields)});\n"
            self.emit_sql("PRIMARY_KEY", sql, destino)
            return sql
        return ""
    
    def generate_create_foreign_key(self, table_name, fk_name, fk_info, destino):
        """
        Genera SQL para crear foreign key.
        
        Args:
            table_name (str): Nombre de la tabla
            fk_name (str): Nombre de la constraint
            fk_info (dict): Información de la FK
            destino (str): "BD1" o "BD2"
            
        Returns:
            str: Sentencia ALTER TABLE
        """
        fields = ', '.join(fk_info['fields'])
        ref_fields = ', '.join(fk_info['referenced_fields'])
        
        sql = f"ALTER TABLE {table_name} ADD CONSTRAINT {fk_name} "
        sql += f"FOREIGN KEY ({fields}) REFERENCES {fk_info['referenced_table']} ({ref_fields});\n"
        
        self.emit_sql("FOREIGN_KEY", sql, destino)
        return sql
    
    def generate_create_trigger(self, trigger_name, trigger_info, destino):
        """
        Genera SQL para crear un trigger.
        
        Args:
            trigger_name (str): Nombre del trigger
            trigger_info (dict): Información del trigger
            destino (str): "BD1" o "BD2"
            
        Returns:
            str: Sentencia CREATE TRIGGER
        """
        if trigger_name.startswith('RDB$'):
            trigger_name = f"TRG_{trigger_info['table']}_{trigger_name[4:]}"
        
        inactive = "INACTIVE " if trigger_info.get('inactive') else ""
        
        # Tipo de trigger
        trigger_type = trigger_info['type']
        trigger_types = {
            1: "BEFORE INSERT",
            2: "AFTER INSERT", 
            3: "BEFORE UPDATE",
            4: "AFTER UPDATE",
            5: "BEFORE DELETE",
            6: "AFTER DELETE"
        }
        trigger_type_desc = trigger_types.get(trigger_type, f"/* Tipo: {trigger_type} */")
        
        sql = f"CREATE TRIGGER {trigger_name} {inactive}{trigger_type_desc}\n"
        sql += f"FOR {trigger_info['table']}\n"
        sql += f"{trigger_info['source']}\n"
        
        self.emit_sql("TRIGGER", sql, destino)
        return sql
    
    def generate_create_procedure(self, procedure_name, procedure_info, destino):
        """
        Genera SQL para crear stored procedure.
        
        Args:
            procedure_name (str): Nombre del procedure
            procedure_info (dict): Información del procedure
            destino (str): "BD1" o "BD2"
            
        Returns:
            str: Sentencia CREATE PROCEDURE
        """
        if procedure_name.startswith('RDB$'):
            procedure_name = f"SP_{procedure_name[4:]}"
        
        sql = f"CREATE PROCEDURE {procedure_name}\n"
        sql += f"AS\n"
        sql += f"BEGIN\n"
        sql += f"{procedure_info['source']}\n"
        sql += f"END;\n"
        
        self.emit_sql("PROCEDIMIENTO", sql, destino)
        return sql
    
    def generate_create_view(self, view_name, view_definition, destino):
        """
        Genera SQL para crear una vista.
        
        Args:
            view_name (str): Nombre de la vista
            view_definition (str): Definición SQL de la vista
            destino (str): "BD1" o "BD2"
            
        Returns:
            str: Sentencia CREATE VIEW
        """
        if view_name.startswith('RDB$'):
            view_name = f"VW_{view_name[4:]}"
        
        sql = f"CREATE VIEW {view_name} AS\n"
        sql += f"{view_definition};\n"
        
        self.emit_sql("VISTA", sql, destino)
        return sql
    
    def generate_create_generator(self, generator_name, value, destino):
        """
        Genera SQL para crear un generador (sequence).
        
        Args:
            generator_name (str): Nombre del generador
            value (int): Valor inicial
            destino (str): "BD1" o "BD2"
            
        Returns:
            str: Sentencia CREATE GENERATOR
        """
        if generator_name.startswith('RDB$'):
            generator_name = f"GEN_{generator_name[4:]}"
        
        sql = f"CREATE GENERATOR {generator_name};\n"
        if value is not None and value > 0:
            sql += f"SET GENERATOR {generator_name} TO {value};\n"
        
        self.emit_sql("GENERADOR", sql, destino)
        return sql
    def generate_alter_field(self, table_name, campo, props, destino):
        """
        Genera SQL LIMPIO para modificar un campo existente.
        """
        sql_type = self._get_sql_type(props)
        
        # SQL DIRECTO para modificar campo (depende de la versión de Firebird)
        sql = f"ALTER TABLE {table_name} ALTER COLUMN {campo} TYPE {sql_type}"
        
        # Agregar CHARACTER SET si está especificado
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
        
        self.emit_sql("CAMPO", sql, destino)
        return sql
