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
    QGroupBox, QGridLayout, QTabWidget, QTextEdit, QSplitter, QFrame
)
from PyQt5.QtCore import QThread, Qt
from PyQt5.QtGui import QFont, QPalette, QColor
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
        self.setWindowTitle("🔍 Comparador de Bases de Datos Firebird")
        self.resize(1000, 800)
        self._aplicar_estilo_moderno()
        self._build_ui()

    def _aplicar_estilo_moderno(self):
        """Aplica estilos modernos a la aplicación."""
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f7fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #34495e;
            }
            
            QPushButton {
                background-color: #3498db;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            
            QPushButton:hover {
                background-color: #2980b9;
            }
            
            QPushButton:pressed {
                background-color: #21618c;
            }
            
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
            
            QLineEdit {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
            }
            
            QLineEdit:focus {
                border-color: #3498db;
            }
            
            QCheckBox {
                spacing: 8px;
                font-size: 11px;
                color: #2c3e50;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            
            QCheckBox::indicator:unchecked {
                border: 2px solid #bdc3c7;
                background-color: white;
                border-radius: 3px;
            }
            
            QCheckBox::indicator:checked {
                border: 2px solid #3498db;
                background-color: #3498db;
                border-radius: 3px;
            }
            
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                background-color: #ecf0f1;
            }
            
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 3px;
            }
            
            /* ESTILO MEJORADO PARA TEXTEDIT - LETRA MÁS GRANDE */
            QTextEdit {
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
                padding: 8px;
            }
            
            QTextEdit:focus {
                border-color: #3498db;
            }
            
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            
            QTabBar::tab {
                background-color: #ecf0f1;
                color: #2c3e50;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            
            QTabBar::tab:selected {
                background-color: #3498db;
                color: white;
            }
            
            QLabel {
                color: #2c3e50;
                font-size: 11px;
            }
        """)

    def _build_ui(self):
        """Construye todos los componentes de la interfaz."""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = self._crear_header()
        main_layout.addLayout(header)

        # Tabs para organización
        tab_widget = QTabWidget()
        
        # Tab de configuración
        config_tab = self._crear_tab_configuracion()
        tab_widget.addTab(config_tab, "⚙️ Configuración")

        # Tab de SQL
        sql_tab = self._crear_tab_sql()
        tab_widget.addTab(sql_tab, "📊 SQL Generado")

        main_layout.addWidget(tab_widget)

        # Controles principales
        self._agregar_controles_principales(main_layout)

        self.setLayout(main_layout)
        self._configurar_estado_inicial()

    def _crear_header(self):
        """Crea el header de la aplicación."""
        header_layout = QHBoxLayout()
        
        title = QLabel("🔍 Comparador de Bases de Datos Firebird")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        return header_layout

    def _crear_tab_configuracion(self):
        """Crea la pestaña de configuración."""
        config_tab = QWidget()
        config_layout = QVBoxLayout()
        config_layout.setSpacing(15)
        
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
        gbd = QGroupBox("📁 Bases de Datos")
        gb_layout = QGridLayout()
        gb_layout.setSpacing(10)
        
        self.ed_bd1 = QLineEdit()
        self.ed_bd1.setPlaceholderText("Ruta de la base de datos principal (BD1)...")
        btn_bd1 = QPushButton("📂 BD1")
        btn_bd1.clicked.connect(lambda: self._select_file(self.ed_bd1))
        
        self.ed_bd2 = QLineEdit()
        self.ed_bd2.setPlaceholderText("Ruta de la base de datos a comparar (BD2)...")
        btn_bd2 = QPushButton("📂 BD2")
        btn_bd2.clicked.connect(lambda: self._select_file(self.ed_bd2))
        
        gb_layout.addWidget(QLabel("BD1 (Principal):"), 0, 0)
        gb_layout.addWidget(self.ed_bd1, 0, 1)
        gb_layout.addWidget(btn_bd1, 0, 2)
        gb_layout.addWidget(QLabel("BD2 (Comparar):"), 1, 0)
        gb_layout.addWidget(self.ed_bd2, 1, 1)
        gb_layout.addWidget(btn_bd2, 1, 2)
        
        gbd.setLayout(gb_layout)
        return gbd

    def _crear_grupo_credenciales(self):
        """Crea el grupo de credenciales."""
        gcred = QGroupBox("🔐 Credenciales")
        c_layout = QGridLayout()
        c_layout.setSpacing(10)
        
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
        gopt = QGroupBox("🎯 Objetos a Comparar")
        opt_layout = QGridLayout()
        opt_layout.setSpacing(8)
        
        # Checkboxes para objetos a comparar
        self.chk_tablas = QCheckBox("📊 Tablas")
        self.chk_campos = QCheckBox("📋 Campos")
        self.chk_indices = QCheckBox("📈 Índices")
        self.chk_pk = QCheckBox("🔑 Primary Keys")
        self.chk_fk = QCheckBox("🔗 Foreign Keys")
        self.chk_triggers = QCheckBox("⚡ Triggers")
        self.chk_sp = QCheckBox("💾 Procedimientos")
        self.chk_vistas = QCheckBox("👁️ Vistas")
        self.chk_generadores = QCheckBox("🔢 Generadores")
        self.chk_generar_sql = QCheckBox("📝 Generar SQL automáticamente")

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
        sql_layout.setSpacing(10)
        
        # Header para identificar los paneles
        sql_header = QHBoxLayout()
        sql_header.addWidget(QLabel("🔄 SQL para BD2 (sincronizar con BD1)"))
        sql_header.addWidget(QLabel("🔄 SQL para BD1 (sincronizar con BD2)"))
        sql_layout.addLayout(sql_header)
        
        # Splitter para los editores de SQL
        sql_splitter = QSplitter(Qt.Horizontal)
        
        self.sql_bd1 = QTextEdit()
        self.sql_bd1.setPlaceholderText("El SQL para sincronizar BD2 con los objetos de BD1 aparecerá aquí...")
        # AUMENTAR TAMAÑO DE LETRA
        self.sql_bd1.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
                padding: 8px;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        
        self.sql_bd2 = QTextEdit()
        self.sql_bd2.setPlaceholderText("El SQL para sincronizar BD1 con los objetos de BD2 aparecerá aquí...")
        # AUMENTAR TAMAÑO DE LETRA
        self.sql_bd2.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
                padding: 8px;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        
        sql_splitter.addWidget(self.sql_bd1)
        sql_splitter.addWidget(self.sql_bd2)
        sql_splitter.setSizes([450, 450])
        
        # Botones para el SQL
        sql_buttons = self._crear_botones_sql()
        
        sql_layout.addWidget(sql_splitter)
        sql_layout.addLayout(sql_buttons)
        sql_tab.setLayout(sql_layout)
        return sql_tab

    def _crear_botones_sql(self):
        """Crea los botones para manejar el SQL."""
        sql_buttons = QHBoxLayout()
        
        btn_copy_bd1 = QPushButton("📋 Copiar SQL BD1")
        btn_copy_bd1.clicked.connect(lambda: self._copy_sql("BD1"))
        
        btn_copy_bd2 = QPushButton("📋 Copiar SQL BD2")
        btn_copy_bd2.clicked.connect(lambda: self._copy_sql("BD2"))
        
        btn_clear_sql = QPushButton("🗑️ Limpiar SQL")
        btn_clear_sql.clicked.connect(self._clear_sql)
        
        sql_buttons.addWidget(btn_copy_bd1)
        sql_buttons.addWidget(btn_copy_bd2)
        sql_buttons.addWidget(btn_clear_sql)
        sql_buttons.addStretch()
        
        return sql_buttons

    def _agregar_controles_principales(self, layout):
        """Agrega los controles principales al layout."""
        # Barra de progreso
        self.progress = QProgressBar()
        self.progress.setValue(0)
        
        # Etiqueta de estado
        self.lbl_msg = QLabel("✅ Listo para comparar - Solo se generarán diferencias")
        self.lbl_msg.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #d5edda;
                border: 1px solid #c3e6cb;
                border-radius: 4px;
                color: #155724;
            }
        """)
        
        # Botones principales
        hbox = QHBoxLayout()
        
        self.btn_compare = QPushButton("🚀 Comparar y Generar Scripts")
        self.btn_compare.clicked.connect(self._start_comparison)
        
        self.btn_reset = QPushButton("🔄 Nueva Comparación")
        self.btn_reset.clicked.connect(self._reset_app)
        
        hbox.addWidget(self.btn_compare)
        hbox.addWidget(self.btn_reset)
        hbox.addStretch()
        
        layout.addWidget(self.progress)
        layout.addWidget(self.lbl_msg)
        layout.addLayout(hbox)

    def _configurar_estado_inicial(self):
        """Configura el estado inicial de la aplicación."""
        self._on_tablas_toggle()

    # Métodos de eventos y acciones (se mantienen iguales)
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
        QMessageBox.information(self, "✅ Copiado", f"SQL para {bd} copiado al portapapeles")

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
        self.lbl_msg.setText("✅ Listo para nueva comparación - Solo se generarán diferencias")
        self.btn_compare.setEnabled(True)
        self.last_outputs = {"excel": None, "txt": None}
        
        QMessageBox.information(self, "🔄 Reiniciado", "Aplicación reiniciada para nueva comparación")

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
            QMessageBox.warning(self, "⚠️ Faltan datos", "Selecciona ambas bases de datos (BD1 y BD2).")
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
        self.lbl_msg.setText("🔄 Iniciando comparación...")
        self.lbl_msg.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #fff3cd;
                border: 1px solid #ffeaa7;
                border-radius: 4px;
                color: #856404;
            }
        """)

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
        self.lbl_msg.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 4px;
                color: #721c24;
            }
        """)
        QMessageBox.critical(self, "❌ Error durante la comparación", txt)
        self.btn_compare.setEnabled(True)
        self.progress.setValue(0)
        self.lbl_msg.setText("❌ Error")

    def _on_finished(self):
        """Maneja la finalización exitosa de la comparación."""
        self.lbl_msg.setStyleSheet("""
            QLabel {
                padding: 8px;
                background-color: #d5edda;
                border: 1px solid #c3e6cb;
                border-radius: 4px;
                color: #155724;
            }
        """)
        QMessageBox.information(self, "✅ Finalizado", "Comparación completada exitosamente. Se generaron scripts de sincronización.")
        self.btn_compare.setEnabled(True)
        self.progress.setValue(100)
        self.lbl_msg.setText("✅ Comparación finalizada - Scripts generados")