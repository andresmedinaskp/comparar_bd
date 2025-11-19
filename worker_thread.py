"""
Módulo para ejecutar la comparación en un hilo separado.
Contiene la lógica principal de comparación y las señales.
"""

import threading
import traceback
from PyQt5.QtCore import QObject, pyqtSignal
from database_connection import conectar_ruta, get_tables
from sql_generator import SQLGenerator
from comparators import (
    comparar_tablas, comparar_campos_tabla, comparar_indices_pk, 
    comparar_foreign_keys, comparar_triggers, comparar_procedimientos,
    comparar_vistas, comparar_generadores
)
from exporters import exportar_solo_diferencias


class WorkerSignals(QObject):
    """
    Señales para comunicación entre el hilo worker y la interfaz principal.
    """
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    sql_generated = pyqtSignal(str, str)  # tipo_objeto, sql


def run_comparison(worker_signals, bd1, bd2, user, password, options, output_path):
    """
    Ejecuta la comparación completa entre dos bases de datos.
    """
    try:
        # Conexión a bases de datos
        worker_signals.message.emit("Conectando a BD1...")
        c1 = conectar_ruta(bd1, user, password)
        worker_signals.message.emit("Conectando a BD2...")
        c2 = conectar_ruta(bd2, user, password)

        diferencias = []  # Solo almacenar diferencias
        total_steps = 9   # Número total de pasos
        step = 0
        
        sql_generator = SQLGenerator(worker_signals)

        # Ejecutar comparaciones según las opciones seleccionadas
        step = _ejecutar_comparaciones(
            c1, c2, diferencias, sql_generator, options, 
            worker_signals, step, total_steps
        )

        # Exportar resultados - SOLO TXT
        worker_signals.message.emit("Generando archivos TXT...")
        if not output_path:
            output_path = "reporte_comparacion"
        
        # Generar archivos TXT separados para cada BD (PASANDO LAS OPCIONES)
        txt_path_bd1, txt_path_bd2, txt_path_sql = exportar_solo_diferencias(
            output_path, 
            diferencias, 
            sql_generator.get_sql_bd1(), 
            sql_generator.get_sql_bd2(),
            options  # ← AQUÍ SE AGREGAN LAS OPCIONES
        )

        # Enviar SQL final a la interfaz
        worker_signals.sql_generated.emit("SQL_BD1_COMPLETO", sql_generator.get_sql_bd1())
        worker_signals.sql_generated.emit("SQL_BD2_COMPLETO", sql_generator.get_sql_bd2())

        mensaje = _construir_mensaje_final(txt_path_bd1, txt_path_bd2, txt_path_sql)
        worker_signals.message.emit(mensaje)
        worker_signals.finished.emit()

    except Exception as e:
        tb = traceback.format_exc()
        worker_signals.error.emit(f"{str(e)}\n\n{tb}")


def _ejecutar_comparaciones(c1, c2, diferencias, sql_generator, options, worker_signals, step, total_steps):
    """Ejecuta las comparaciones según las opciones seleccionadas."""
    
    # Tablas
    if options.get("tablas"):
        worker_signals.message.emit("Comparando tablas...")
        comparar_tablas(c1, c2, diferencias, sql_generator)
        worker_signals.message.emit(f"Diferencias en tablas: {len([f for f in diferencias if f[0] == 'Tablas'])}")
    
    step += 1
    worker_signals.progress.emit(int((step / total_steps) * 100))

    # Campos (solo si se seleccionaron tablas)
    if options.get("campos") and options.get("tablas"):
        worker_signals.message.emit("Comparando campos...")
        tablas_comunes = sorted(set(get_tables(c1)) & set(get_tables(c2)))
        count = len(tablas_comunes)
        for idx, t in enumerate(tablas_comunes, start=1):
            comparar_campos_tabla(c1, c2, t, diferencias, sql_generator)
            if count:
                worker_signals.progress.emit(int(((step + idx / count) / total_steps) * 100))
        
        total_campos = len([f for f in diferencias if 'Campos_' in f[0]])
        worker_signals.message.emit(f"Diferencias en campos: {total_campos}")
    
    step += 1
    worker_signals.progress.emit(int((step / total_steps) * 100))

    # Índices y PK (AHORA INDEPENDIENTE DE LAS TABLAS)
    if options.get("indices") or options.get("pk"):
        worker_signals.message.emit("Comparando índices y PK...")
        comparar_indices_pk(c1, c2, diferencias, sql_generator)  # ← YA NO DEPENDE DE TABLAS_COMUNES
    step += 1
    worker_signals.progress.emit(int((step / total_steps) * 100))

    # Foreign Keys (solo si se seleccionaron tablas)
    if options.get("fk") and options.get("tablas"):
        worker_signals.message.emit("Comparando llaves foráneas...")
        tablas_comunes = sorted(set(get_tables(c1)) & set(get_tables(c2)))
        for t in tablas_comunes:
            comparar_foreign_keys(c1, c2, t, diferencias, sql_generator)
    step += 1
    worker_signals.progress.emit(int((step / total_steps) * 100))

    # Triggers
    if options.get("triggers"):
        worker_signals.message.emit("Comparando triggers...")
        comparar_triggers(c1, c2, diferencias, sql_generator)
    step += 1
    worker_signals.progress.emit(int((step / total_steps) * 100))

    # Procedimientos
    if options.get("procedimientos"):
        worker_signals.message.emit("Comparando procedimientos...")
        comparar_procedimientos(c1, c2, diferencias, sql_generator)
    step += 1
    worker_signals.progress.emit(int((step / total_steps) * 100))

    # Vistas
    if options.get("vistas"):
        worker_signals.message.emit("Comparando vistas...")
        comparar_vistas(c1, c2, diferencias, sql_generator)
    step += 1
    worker_signals.progress.emit(int((step / total_steps) * 100))

    # Generadores
    if options.get("generadores"):
        worker_signals.message.emit("Comparando generadores...")
        comparar_generadores(c1, c2, diferencias, sql_generator)
    step += 1
    worker_signals.progress.emit(int((step / total_steps) * 100))

    return step

def _construir_mensaje_final(txt_path_bd1, txt_path_bd2, txt_path_sql):
    """
    Construye el mensaje final con las rutas de los archivos generados.
    """
    mensaje = "Archivos TXT generados:\n"
    if txt_path_bd1:
        mensaje += f"Scripts BD1: {txt_path_bd1}\n"
    if txt_path_bd2:
        mensaje += f"Scripts BD2: {txt_path_bd2}\n"
    if txt_path_sql:
        mensaje += f"SQL Completo: {txt_path_sql}"
    return mensaje