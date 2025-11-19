"""
Módulo principal de la aplicación con la interfaz gráfica.
Contiene la clase MainApp que maneja la interfaz de usuario.
"""

import sys
import os
import threading
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog, QLineEdit,
    QVBoxLayout, QHBoxLayout, QCheckBox, QMessageBox, QProgressBar, 
    QGroupBox, QGridLayout, QTabWidget, QTextEdit, QSplitter
)
from PyQt5.QtCore import QThread
from worker_thread import WorkerSignals, run_comparison


class MainApp(QWidget):
    """
    Clase principal de la aplicación que maneja la interfaz gráfica.
    """
    
    def __init__(self):
        """Inicializa la aplicación principal."""
        super().__init__()
        self.signals = None
        self.sql_content = {"BD1": "", "BD2": ""}
        self.last_outputs = {"excel": None, "txt": None}
        self._inicializar_interfaz()

    def _inicializar_interfaz(self):
        """Configura la interfaz gráfica de usuario."""
        self.setWindowTitle("Comparador Firebird - Solo Diferencias")
        self.resize(900, 700)
        self._build_ui()

    def _build_ui(self):
        """Construye todos los componentes de la interfaz."""
        main_layout = QVBoxLayout()

        # Tabs para organización
        tab_widget = QTabWidget()
        
        # Tab de configuración
        config_tab = self._crear_tab_configuracion()
        tab_widget.addTab(config_tab, "Configuración")

        # Tab de SQL
        sql_tab = self._crear_tab_sql()
        tab_widget.addTab(sql_tab, "SQL Generado")

        main_layout.addWidget(tab_widget)

        # Botones y controles principales
        self._agregar_controles_principales(main_layout)

        self.setLayout(main_layout)
        self._configurar_estado_inicial()

    def _crear_tab_configuracion(self):
        """Crea la pestaña de configuración."""
        config_tab = QWidget()
        config_layout = QVBoxLayout()
        
        # Grupo de bases de datos
        gbd = self._crear_grupo_bases_datos()
        config_layout.addWidget(gbd)

        # Grupo de credenciales
        gcred = self._crear_grupo_credenciales()
        config_layout.addWidget(gcred)

        # Grupo de opciones
        gopt = self._crear_grupo_opciones()
        config_layout.addWidget(gopt)

        config_tab.setLayout(config_layout)
        return config_tab

    def _crear_grupo_bases_datos(self):
        """Crea el grupo de selección de bases de datos."""
        gbd = QGroupBox("Bases de datos")
        gb_layout = QGridLayout()
        
        self.ed_bd1 = QLineEdit()
        self.ed_bd1.setPlaceholderText("Ruta de la base de datos principal (BD1)")
        btn_bd1 = QPushButton("Seleccionar BD1")
        btn_bd1.clicked.connect(lambda: self._select_file(self.ed_bd1))
        
        self.ed_bd2 = QLineEdit()
        self.ed_bd2.setPlaceholderText("Ruta de la base de datos a comparar (BD2)")
        btn_bd2 = QPushButton("Seleccionar BD2")
        btn_bd2.clicked.connect(lambda: self._select_file(self.ed_bd2))
        
        gb_layout.addWidget(QLabel("BD1 (principal):"), 0, 0)
        gb_layout.addWidget(self.ed_bd1, 0, 1)
        gb_layout.addWidget(btn_bd1, 0, 2)
        gb_layout.addWidget(QLabel("BD2 (comparar):"), 1, 0)
        gb_layout.addWidget(self.ed_bd2, 1, 1)
        gb_layout.addWidget(btn_bd2, 1, 2)
        
        gbd.setLayout(gb_layout)
        return gbd

    def _crear_grupo_credenciales(self):
        """Crea el grupo de credenciales."""
        gcred = QGroupBox("Credenciales")
        c_layout = QGridLayout()
        
        self.ed_user = QLineEdit()
        self.ed_user.setText("SYSDBA")
        self.ed_user.setPlaceholderText("Usuario de la base de datos")
        
        self.ed_pass = QLineEdit()
        self.ed_pass.setEchoMode(QLineEdit.Password)
        self.ed_pass.setText("masterkey")
        self.ed_pass.setPlaceholderText("Contraseña")
        
        c_layout.addWidget(QLabel("Usuario:"), 0, 0)
        c_layout.addWidget(self.ed_user, 0, 1)
        c_layout.addWidget(QLabel("Contraseña:"), 1, 0)
        c_layout.addWidget(self.ed_pass, 1, 1)
        
        gcred.setLayout(c_layout)
        return gcred

    def _crear_grupo_opciones(self):
        """Crea el grupo de opciones de comparación."""
        gopt = QGroupBox("Objetos a comparar")
        opt_layout = QGridLayout()
        
        # Checkboxes para objetos a comparar
        self.chk_tablas = QCheckBox("Tablas")
        self.chk_campos = QCheckBox("Campos")
        self.chk_indices = QCheckBox("Índices")
        self.chk_pk = QCheckBox("Primary Keys")
        self.chk_fk = QCheckBox("Foreign Keys")
        self.chk_triggers = QCheckBox("Triggers")
        self.chk_sp = QCheckBox("Procedimientos")
        self.chk_vistas = QCheckBox("Vistas")
        self.chk_generadores = QCheckBox("Generadores")
        self.chk_generar_sql = QCheckBox("Generar SQL automáticamente")

        # Valores por defecto
        for checkbox in [self.chk_tablas, self.chk_campos, self.chk_indices, 
                        self.chk_pk, self.chk_fk, self.chk_triggers, 
                        self.chk_sp, self.chk_vistas, self.chk_generadores, 
                        self.chk_generar_sql]:
            checkbox.setChecked(True)

        self.chk_tablas.stateChanged.connect(self._on_tablas_toggle)

        # Organizar en grid
        opt_layout.addWidget(self.chk_tablas, 0, 0)
        opt_layout.addWidget(self.chk_campos, 0, 1)
        opt_layout.addWidget(self.chk_indices, 1, 0)
        opt_layout.addWidget(self.chk_pk, 1, 1)
        opt_layout.addWidget(self.chk_fk, 2, 0)
        opt_layout.addWidget(self.chk_triggers, 2, 1)
        opt_layout.addWidget(self.chk_sp, 3, 0)
        opt_layout.addWidget(self.chk_vistas, 3, 1)
        opt_layout.addWidget(self.chk_generadores, 4, 0)
        opt_layout.addWidget(self.chk_generar_sql, 4, 1)
        
        gopt.setLayout(opt_layout)
        return gopt

    def _crear_tab_sql(self):
        """Crea la pestaña de SQL generado."""
        sql_tab = QWidget()
        sql_layout = QVBoxLayout()
        
        # Header para identificar los paneles
        sql_header = QHBoxLayout()
        sql_header.addWidget(QLabel("SQL para BD2 (crear objetos faltantes de BD1)"))
        sql_header.addWidget(QLabel("SQL para BD1 (crear objetos faltantes de BD2)"))
        sql_layout.addLayout(sql_header)
        
        # Splitter para los editores de SQL
        sql_splitter = QSplitter()
        
        self.sql_bd1 = QTextEdit()
        self.sql_bd1.setPlaceholderText("Aquí aparecerá el SQL para sincronizar BD2 con los objetos de BD1...")
        
        self.sql_bd2 = QTextEdit()
        self.sql_bd2.setPlaceholderText("Aquí aparecerá el SQL para sincronizar BD1 con los objetos de BD2...")
        
        sql_splitter.addWidget(self.sql_bd1)
        sql_splitter.addWidget(self.sql_bd2)
        sql_splitter.setSizes([400, 400])
        
        # Botones para el SQL
        sql_buttons = self._crear_botones_sql()
        
        sql_layout.addWidget(sql_splitter)
        sql_layout.addLayout(sql_buttons)
        sql_tab.setLayout(sql_layout)
        return sql_tab

    def _crear_botones_sql(self):
        """Crea los botones para manejar el SQL."""
        sql_buttons = QHBoxLayout()
        
        btn_copy_bd1 = QPushButton("Copiar SQL BD1")
        btn_copy_bd1.clicked.connect(lambda: self._copy_sql("BD1"))
        
        btn_copy_bd2 = QPushButton("Copiar SQL BD2")
        btn_copy_bd2.clicked.connect(lambda: self._copy_sql("BD2"))
        
        btn_clear_sql = QPushButton("Limpiar SQL")
        btn_clear_sql.clicked.connect(self._clear_sql)
        
        sql_buttons.addWidget(btn_copy_bd1)
        sql_buttons.addWidget(btn_copy_bd2)
        sql_buttons.addWidget(btn_clear_sql)
        sql_buttons.addStretch()
        
        return sql_buttons

    def _agregar_controles_principales(self, layout):
        """Agrega los controles principales al layout."""
        # Botones principales
        hbox = QHBoxLayout()
        
        self.btn_compare = QPushButton("Comparar y Generar Reporte")
        self.btn_compare.clicked.connect(self._start_comparison)
        
        self.btn_open = QPushButton("Abrir Reporte")
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self._open_last_report)
        
        self.btn_reset = QPushButton("Nueva Comparación")
        self.btn_reset.clicked.connect(self._reset_app)
        
        hbox.addWidget(self.btn_compare)
        hbox.addWidget(self.btn_open)
        hbox.addWidget(self.btn_reset)
        layout.addLayout(hbox)

        # Barra de progreso y mensajes
        self.progress = QProgressBar()
        self.progress.setValue(0)
        
        self.lbl_msg = QLabel("Listo para comparar - Solo se generarán diferencias")
        
        layout.addWidget(self.progress)
        layout.addWidget(self.lbl_msg)

    def _configurar_estado_inicial(self):
        """Configura el estado inicial de la aplicación."""
        self._on_tablas_toggle()

    # Métodos de eventos y acciones
    def _select_file(self, control):
        """Abre diálogo para seleccionar archivo de base de datos."""
        file, _ = QFileDialog.getOpenFileName(
            self, 
            "Seleccionar Base de Datos Firebird", 
            "", 
            "Firebird (*.fdb *.fdb3 *.FDB);;Todos (*)"
        )
        if file:
            control.setText(file)

    def _on_tablas_toggle(self):
        """Habilita/deshabilita opciones dependientes de tablas."""
        activar = self.chk_tablas.isChecked()
        for checkbox in [self.chk_campos, self.chk_indices, self.chk_pk, self.chk_fk]:
            checkbox.setEnabled(activar)

    def _copy_sql(self, bd):
        """Copia el SQL al portapapeles."""
        text = self.sql_bd1.toPlainText() if bd == "BD1" else self.sql_bd2.toPlainText()
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "Copiado", f"SQL para {bd} copiado al portapapeles")

    def _clear_sql(self):
        """Limpia los editores de SQL."""
        self.sql_bd1.clear()
        self.sql_bd2.clear()
        self.sql_content = {"BD1": "", "BD2": ""}

    def _reset_app(self):
        """Reinicia la aplicación para una nueva comparación."""
        # Limpiar campos
        self.ed_bd1.clear()
        self.ed_bd2.clear()
        self.ed_user.setText("SYSDBA")
        self.ed_pass.setText("masterkey")
        
        # Restablecer checkboxes
        for checkbox in [self.chk_tablas, self.chk_campos, self.chk_indices, 
                        self.chk_pk, self.chk_fk, self.chk_triggers, 
                        self.chk_sp, self.chk_vistas, self.chk_generadores, 
                        self.chk_generar_sql]:
            checkbox.setChecked(True)
        
        # Limpiar SQL y estado
        self._clear_sql()
        self.progress.setValue(0)
        self.lbl_msg.setText("Listo para nueva comparación - Solo se generarán diferencias")
        self.btn_open.setEnabled(False)
        self.btn_compare.setEnabled(True)
        self.last_outputs = {"excel": None, "txt": None}
        
        QMessageBox.information(self, "Reiniciado", "Aplicación reiniciada para nueva comparación")

    def _on_sql_generated(self, tipo, sql):
        """Maneja la recepción de SQL generado."""
        if tipo == "SQL_BD1_COMPLETO":
            self.sql_bd1.setPlainText(sql)
            self.sql_content["BD1"] = sql
        elif tipo == "SQL_BD2_COMPLETO":
            self.sql_bd2.setPlainText(sql)
            self.sql_content["BD2"] = sql

    def _start_comparison(self):
        """Inicia el proceso de comparación."""
        # Validar datos
        bd1 = self.ed_bd1.text().strip()
        bd2 = self.ed_bd2.text().strip()
        user = self.ed_user.text().strip()
        password = self.ed_pass.text().strip()

        if not bd1 or not bd2:
            QMessageBox.warning(self, "Faltan datos", "Selecciona ambas bases de datos (BD1 y BD2).")
            return

        # Obtener ruta para guardar
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Guardar reporte", 
            "reporte_comparacion", 
            "Todos los archivos (*)"
        )
        if not save_path:
            return

        # Remover extensión si existe
        if '.' in save_path:
            save_path = save_path.rsplit('.', 1)[0]

        # Preparar opciones
        options = self._obtener_opciones()

        # Configurar interfaz para comparación
        self._preparar_ui_para_comparacion()

        # Limpiar SQL anterior si es necesario
        if options["generar_sql"]:
            self._clear_sql()

        # Configurar y lanzar hilo de comparación
        self._configurar_y_lanzar_hilo(bd1, bd2, user, password, options, save_path)

    def _obtener_opciones(self):
        """Obtiene las opciones seleccionadas por el usuario."""
        return {
            "tablas": self.chk_tablas.isChecked(),
            "campos": self.chk_campos.isChecked(),
            "indices": self.chk_indices.isChecked(),
            "pk": self.chk_pk.isChecked(),
            "fk": self.chk_fk.isChecked(),
            "triggers": self.chk_triggers.isChecked(),
            "procedimientos": self.chk_sp.isChecked(),
            "vistas": self.chk_vistas.isChecked(),
            "generadores": self.chk_generadores.isChecked(),
            "generar_sql": self.chk_generar_sql.isChecked()
        }

    def _preparar_ui_para_comparacion(self):
        """Prepara la UI para comenzar la comparación."""
        self.btn_compare.setEnabled(False)
        self.progress.setValue(0)
        self.lbl_msg.setText("Iniciando comparación...")
        self.btn_open.setEnabled(False)

    def _configurar_y_lanzar_hilo(self, bd1, bd2, user, password, options, save_path):
        """Configura y lanza el hilo de comparación."""
        self.signals = WorkerSignals()
        self.signals.progress.connect(self._on_progress)
        self.signals.message.connect(self._on_message)
        self.signals.error.connect(self._on_error)
        self.signals.finished.connect(self._on_finished)
        
        # SIEMPRE conectar las señales de SQL, no solo si options["generar_sql"]
        self.signals.sql_generated.connect(self._on_sql_generated)

        # Lanzar en hilo separado
        thread = threading.Thread(
            target=run_comparison, 
            args=(self.signals, bd1, bd2, user, password, options, save_path), 
            daemon=True
        )
        thread.start()

    def _on_progress(self, val):
        """Actualiza la barra de progreso."""
        self.progress.setValue(val)

    def _on_message(self, txt):
        """Actualiza el mensaje de estado."""
        self.lbl_msg.setText(txt)

    def _on_error(self, txt):
        """Maneja errores durante la comparación."""
        QMessageBox.critical(self, "Error durante la comparación", txt)
        self.btn_compare.setEnabled(True)
        self.btn_open.setEnabled(False)
        self.progress.setValue(0)
        self.lbl_msg.setText("Error")

    def _on_finished(self):
        """Maneja la finalización exitosa de la comparación."""
        QMessageBox.information(self, "Finalizado", "Comparación finalizada. Solo se generaron diferencias.")
        self.btn_compare.setEnabled(True)
        self.btn_open.setEnabled(True)
        self.progress.setValue(100)
        self.lbl_msg.setText("Listo")

    def _open_last_report(self):
        """Abre los últimos reportes generados."""
        import os
        import subprocess
        
        # Intentar abrir los archivos TXT generados
        files_to_open = []
        
        if self.last_outputs.get("txt_bd1") and os.path.exists(self.last_outputs["txt_bd1"]):
            files_to_open.append(self.last_outputs["txt_bd1"])
        
        if self.last_outputs.get("txt_bd2") and os.path.exists(self.last_outputs["txt_bd2"]):
            files_to_open.append(self.last_outputs["txt_bd2"])
            
        if self.last_outputs.get("txt_sql") and os.path.exists(self.last_outputs["txt_sql"]):
            files_to_open.append(self.last_outputs["txt_sql"])
        
        if files_to_open:
            for file_path in files_to_open:
                try:
                    # Windows
                    os.startfile(file_path)
                except AttributeError:
                    try:
                        # macOS
                        subprocess.run(['open', file_path])
                    except:
                        try:
                            # Linux
                            subprocess.run(['xdg-open', file_path])
                        except:
                            QMessageBox.information(self, "Archivo generado", f"Archivo: {file_path}")
        else:
            QMessageBox.warning(self, "No disponible", "No se encontraron archivos TXT generados")